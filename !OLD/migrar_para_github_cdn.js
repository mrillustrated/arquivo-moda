const fs = require("fs");

const USUARIO = "mrillustrated";
const REPO = "arquivo-moda";
const BRANCH = "main";

const BASE = `https://cdn.jsdelivr.net/gh/${USUARIO}/${REPO}@${BRANCH}/images/`;

const texto = fs.readFileSync("data.js", "utf8");

const codigo = texto + "\nmodule.exports = data;";
const modulo = { exports: null };
new Function("module", codigo)(modulo);

const data = modulo.exports;

function limparCaminho(url) {
  if (!url) return "";

  let caminho = String(url);

  if (caminho.includes("arquivo-desfiles/")) {
    caminho = caminho.split("arquivo-desfiles/")[1];
  }

  if (caminho.includes("/images/")) {
    caminho = caminho.split("/images/")[1];
  }

  if (caminho.startsWith("images/")) {
    caminho = caminho.replace("images/", "");
  }

  caminho = decodeURIComponent(caminho);

  return caminho;
}

data.forEach(item => {
  const caminho = limparCaminho(item.image);

  if (!caminho) return;

  item.image = BASE + caminho;
  item.thumb = BASE + caminho;
});

const novo = "const data = " + JSON.stringify(data, null, 2) + ";\n";

fs.writeFileSync("data_github.js", novo, "utf8");

console.log("Pronto: data_github.js criado");
console.log("Total de itens:", data.length);
