const http = require('http');

function createServer(port, name) {
  const server = http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
    res.end(`ok:${name}:${port}\n`);
  });
  server.listen(port, '0.0.0.0', () => {
    console.log(`[node-multiport] ${name} listening on ${port}`);
  });
}

createServer(3000, 'web');
createServer(3001, 'admin');
