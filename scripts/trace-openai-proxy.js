#!/usr/bin/env node
'use strict';

const fs = require('fs');
const http = require('http');
const https = require('https');
const path = require('path');

function parseArgs(argv) {
  const args = {
    host: '127.0.0.1',
    listen: 8090,
    target: 'http://127.0.0.1:8080',
    log: path.join(process.cwd(), 'logs', 'openai-proxy-trace.jsonl'),
    maxChars: Number(process.env.TRACE_MAX_CHARS || 2000000),
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = argv[index + 1];
    if (arg === '--host') {
      args.host = next;
      index += 1;
    } else if (arg === '--listen') {
      args.listen = Number(next);
      index += 1;
    } else if (arg === '--target') {
      args.target = next;
      index += 1;
    } else if (arg === '--log') {
      args.log = next;
      index += 1;
    } else if (arg === '--max-chars') {
      args.maxChars = Number(next);
      index += 1;
    } else if (arg === '--help' || arg === '-h') {
      printHelp();
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  return args;
}

function printHelp() {
  console.log(`Usage: node scripts/trace-openai-proxy.js [options]

Options:
  --host <host>          Listen host. Default: 127.0.0.1
  --listen <port>       Listen port. Default: 8090
  --target <url>        Upstream llama-server base URL. Default: http://127.0.0.1:8080
  --log <path>          JSONL trace output. Default: logs/openai-proxy-trace.jsonl
  --max-chars <n>       Max chars stored per body; 0 disables truncation. Default: 2000000

Point Copilot at http://127.0.0.1:<listen>/v1 while llama-server stays on the target port.`);
}

function readRequestBody(request) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    request.on('data', chunk => chunks.push(chunk));
    request.on('end', () => resolve(Buffer.concat(chunks)));
    request.on('error', reject);
  });
}

function limitBody(text, maxChars) {
  if (maxChars > 0 && text.length > maxChars) {
    return {
      body: text.slice(0, maxChars),
      truncated: true,
      originalChars: text.length,
    };
  }
  return {
    body: text,
    truncated: false,
    originalChars: text.length,
  };
}

function safeParseJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function summarizeRequest(bodyText) {
  const json = safeParseJson(bodyText);
  if (!json) {
    return null;
  }

  return {
    model: json.model,
    stream: json.stream,
    tool_choice: json.tool_choice,
    max_tokens: json.max_tokens,
    temperature: json.temperature,
    messages: Array.isArray(json.messages)
      ? json.messages.map(message => ({
          role: message.role,
          hasToolCalls: Boolean(message.tool_calls),
          contentChars: typeof message.content === 'string' ? message.content.length : undefined,
        }))
      : undefined,
    tools: Array.isArray(json.tools)
      ? json.tools.map(tool => tool && tool.function && tool.function.name).filter(Boolean)
      : undefined,
  };
}

function collectResponseSummary(bodyText) {
  const json = safeParseJson(bodyText);
  if (json) {
    const choices = Array.isArray(json.choices) ? json.choices : [];
    const toolCalls = [];
    let hasReasoning = false;
    let hasContentToolXml = false;

    for (const choice of choices) {
      const message = choice.message || {};
      if (message.reasoning_content) {
        hasReasoning = true;
        hasContentToolXml = hasContentToolXml || String(message.reasoning_content).includes('<tool_call>');
      }
      if (message.content) {
        hasContentToolXml = hasContentToolXml || String(message.content).includes('<tool_call>');
      }
      if (Array.isArray(message.tool_calls)) {
        for (const call of message.tool_calls) {
          toolCalls.push(call.function && call.function.name ? call.function.name : call.type || 'tool_call');
        }
      }
    }

    return {
      mode: 'json',
      finishReasons: choices.map(choice => choice.finish_reason),
      toolCallCount: toolCalls.length,
      toolCallNames: toolCalls,
      hasReasoningContent: hasReasoning,
      hasToolXmlInContentOrReasoning: hasContentToolXml,
    };
  }

  const lines = bodyText.split(/\r?\n/);
  const finishReasons = [];
  const toolCallsByIndex = new Map();
  let hasReasoning = false;
  let hasContentToolXml = false;

  for (const line of lines) {
    if (!line.startsWith('data:')) {
      continue;
    }
    const payload = line.slice(5).trim();
    if (!payload || payload === '[DONE]') {
      continue;
    }
    const chunk = safeParseJson(payload);
    if (!chunk || !Array.isArray(chunk.choices)) {
      continue;
    }
    for (const choice of chunk.choices) {
      if (choice.finish_reason) {
        finishReasons.push(choice.finish_reason);
      }
      const delta = choice.delta || {};
      if (delta.reasoning_content) {
        hasReasoning = true;
        hasContentToolXml = hasContentToolXml || String(delta.reasoning_content).includes('<tool_call>');
      }
      if (delta.content) {
        hasContentToolXml = hasContentToolXml || String(delta.content).includes('<tool_call>');
      }
      if (Array.isArray(delta.tool_calls)) {
        for (const call of delta.tool_calls) {
          const key = call.index !== undefined ? String(call.index) : call.id || String(toolCallsByIndex.size);
          const previous = toolCallsByIndex.get(key) || {};
          const name = call.function && call.function.name ? call.function.name : call.type || 'tool_call';
          toolCallsByIndex.set(key, { name: name !== 'tool_call' ? name : previous.name || name });
        }
      }
    }
  }

  const toolCalls = Array.from(toolCallsByIndex.values()).map(call => call.name || 'tool_call');

  return {
    mode: 'sse-or-text',
    finishReasons,
    toolCallCount: toolCalls.length,
    toolCallNames: toolCalls,
    hasReasoningContent: hasReasoning,
    hasToolXmlInContentOrReasoning: hasContentToolXml,
  };
}

function buildHeaders(incomingHeaders, targetUrl, bodyLength) {
  const headers = { ...incomingHeaders };
  for (const name of [
    'connection',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailer',
    'transfer-encoding',
    'upgrade',
  ]) {
    delete headers[name];
  }
  headers.host = targetUrl.host;
  headers['accept-encoding'] = 'identity';
  headers['content-length'] = String(bodyLength);
  return headers;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const targetBase = new URL(args.target);
  const transport = targetBase.protocol === 'https:' ? https : http;
  fs.mkdirSync(path.dirname(args.log), { recursive: true });

  let requestNumber = 0;

  const server = http.createServer(async (clientReq, clientRes) => {
    const id = `${Date.now()}-${++requestNumber}`;
    const startedAt = new Date();
    const requestBodyBuffer = await readRequestBody(clientReq);
    const requestBodyText = requestBodyBuffer.toString('utf8');
    const targetUrl = new URL(clientReq.url, targetBase);

    const entry = {
      id,
      startedAt: startedAt.toISOString(),
      method: clientReq.method,
      path: clientReq.url,
      target: targetUrl.toString(),
      requestSummary: summarizeRequest(requestBodyText),
    };
    Object.assign(entry, {
      requestBody: limitBody(requestBodyText, args.maxChars).body,
      requestBodyTruncated: limitBody(requestBodyText, args.maxChars).truncated,
    });

    const headers = buildHeaders(clientReq.headers, targetUrl, requestBodyBuffer.length);
    const options = {
      protocol: targetUrl.protocol,
      hostname: targetUrl.hostname,
      port: targetUrl.port || (targetUrl.protocol === 'https:' ? 443 : 80),
      method: clientReq.method,
      path: `${targetUrl.pathname}${targetUrl.search}`,
      headers,
    };

    const upstreamReq = transport.request(options, upstreamRes => {
      clientRes.writeHead(upstreamRes.statusCode || 502, upstreamRes.headers);
      const responseChunks = [];

      upstreamRes.on('data', chunk => {
        responseChunks.push(chunk);
        clientRes.write(chunk);
      });

      upstreamRes.on('end', () => {
        clientRes.end();
        const responseBodyText = Buffer.concat(responseChunks).toString('utf8');
        const limited = limitBody(responseBodyText, args.maxChars);
        entry.durationMs = Date.now() - startedAt.getTime();
        entry.responseStatus = upstreamRes.statusCode;
        entry.responseHeaders = upstreamRes.headers;
        entry.responseBody = limited.body;
        entry.responseBodyTruncated = limited.truncated;
        entry.responseSummary = collectResponseSummary(responseBodyText);
        fs.appendFileSync(args.log, `${JSON.stringify(entry)}\n`, 'utf8');

        const summary = entry.responseSummary;
        console.log(`${entry.startedAt} ${entry.method} ${entry.path} -> ${entry.responseStatus} ${entry.durationMs}ms toolCalls=${summary.toolCallCount} reasoning=${summary.hasReasoningContent}`);
      });
    });

    upstreamReq.on('error', error => {
      entry.durationMs = Date.now() - startedAt.getTime();
      entry.error = error.message;
      fs.appendFileSync(args.log, `${JSON.stringify(entry)}\n`, 'utf8');
      clientRes.writeHead(502, { 'content-type': 'application/json' });
      clientRes.end(JSON.stringify({ error: { message: error.message, type: 'proxy_error' } }));
      console.error(`${entry.startedAt} ${entry.method} ${entry.path} -> proxy error: ${error.message}`);
    });

    upstreamReq.end(requestBodyBuffer);
  });

  server.listen(args.listen, args.host, () => {
    console.log(`OpenAI trace proxy listening on http://${args.host}:${args.listen}`);
    console.log(`Forwarding to ${targetBase.toString()}`);
    console.log(`Writing trace to ${args.log}`);
  });
}

main().catch(error => {
  console.error(error.stack || error.message);
  process.exit(1);
});