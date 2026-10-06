const http = require('http');
const port = process.env.PORT || 3000;
http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain; charset=utf-8' });
  res.end('hello from node-awdp-basic\n');
}).listen(port, '0.0.0.0', () => {
  console.log(`node-awdp-basic listening on ${port}`);
});
