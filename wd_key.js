// 取 WorkBuddy at-rest 密钥（仅经管道输出，不落盘）
// 用法：ELECTRON_RUN_AS_NODE=1 WorkBuddy.exe wd_key.js
try {
  const binding = process._linkedBinding('electron_browser_workbuddy_storage');
  const payload = JSON.parse(binding.loggerGet());
  if (payload && payload.version === 1 && typeof payload.atRestSecretKey === 'string') {
    const crypto = require('crypto');
    const key = crypto.createHash('sha256').update(payload.atRestSecretKey, 'utf8').digest();
    process.stdout.write('WD_KEY ' + key.toString('base64') + '\n');
    process.exit(0);
  }
  process.stderr.write('payload schema mismatch');
  process.exit(4);
} catch (e) {
  process.stderr.write(String(e));
  process.exit(4);
}
