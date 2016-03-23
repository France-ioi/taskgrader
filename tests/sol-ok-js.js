// This solution is a valid Node.js solution

process.stdin.resume();
process.stdin.setEncoding('utf8');

process.stdin.on('data', function (n) {
  process.stdout.write(parseInt(n)*2 + "\n");
});
