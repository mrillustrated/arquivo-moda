const fs = require("fs");

const CLOUD_NAME = "dz3uocw2h";
const PASTA_CLOUDINARY = "arquivo-desfiles";

const texto = fs.readFileSync("data.js", "utf8");

const codigo = texto + "\nmodule.exports = data;";
const modulo = { exports: null };

const func = new Function("module", codigo);
func(modulo);

const data = modulo.exports;

data.forEach(item => {
  if (item.image && item.image.startsWith("images/")) {
    const caminho = item.image.replace("images/", "");
    item.image = `https://res.cloudinary.com/${CLOUD_NAME}/image/upload/${PASTA_CLOUDINARY}/${caminho}`;
  }
});

const novoArquivo = "const data = " + JSON.stringify(data, null, 2) + ";\n";

fs.writeFileSync("data_cloud.js", novoArquivo, "utf8");

console.log("Pronto: data_cloud.js criado");
console.log("Total de itens:", data.length);