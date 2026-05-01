const fs = require("fs");

const texto = fs.readFileSync("data.js", "utf8");

// transforma o data.js em objeto JS
const codigo = texto + "\nmodule.exports = data;";
const modulo = { exports: null };
new Function("module", codigo)(modulo);

const data = modulo.exports;

// adiciona ano como tag
data.forEach(item => {
  const ano = String(item.ano);

  if (!item.tags) item.tags = [];

  if (!item.tags.includes(ano)) {
    item.tags.push(ano);
  }
});

// salva de volta
const novo = "const data = " + JSON.stringify(data, null, 2) + ";\n";

fs.writeFileSync("data.js", novo, "utf8");

console.log("Ano adicionado como tag com sucesso");