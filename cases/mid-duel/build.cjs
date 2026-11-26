// Rebuild from reviewed public sources. Requires the marked package.
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const {marked} = await import(require('node:url').pathToFileURL(require.resolve('marked')).href);
  const dest = path.resolve(__dirname, '../../docs/mid-duel');
  const html = fs.readFileSync(path.join(__dirname, 'page-template.html'), 'utf8')
    .replace('@@TASK@@', marked.parse(fs.readFileSync(path.join(__dirname, 'task.md'), 'utf8')));
  fs.writeFileSync(path.join(dest, 'index.html'), html);
  for (const file of ['case.css','case.js','task.md']) fs.copyFileSync(path.join(__dirname,file),path.join(dest,file));
})();
