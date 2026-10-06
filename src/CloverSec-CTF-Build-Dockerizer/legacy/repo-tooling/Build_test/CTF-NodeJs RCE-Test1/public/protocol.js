(function () {
  // 这一段是给“懂的人”的提示
  const codes = [
    48, 49, 50, 51, 52, 53, 54, 55, 57,
    33, 46, 45, 43, 42, 47,             
    40, 41, 91, 93                    
  ];

  const chars = String.fromCharCode.apply(null, codes);

  const hint = [
    'WAF telemetry snapshot:',
    'allowed-set="' + chars + '"',
    'pattern ~= ^[allowed]+$'
  ].join(' ');

  console.log(hint);
})();

