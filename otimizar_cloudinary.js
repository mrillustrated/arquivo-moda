const fs = require("fs");

const texto = fs.readFileSync("data.js", "utf8");

const codigo = texto + "\nmodule.exports = data;";
const modulo = { exports: null };
new Function("module", codigo)(modulo);

const data = modulo.exports;

data.forEach(item => {
  if (!item.image) return;

  if (item.image.includes("/image/upload/") && !item.image.includes("/f_auto,q_auto/")) {
    item.image = item.image.replace(
      "/image/upload/",
      "/image/upload/f_auto,q_auto,w_1200/"
    );
  }

  item.thumb = item.image.replace(
    "/image/upload/f_auto,q_auto,w_1200/",
    "/image/upload/f_auto,q_auto,w_420/"
  );
});

const novo = "const data = " + JSON.stringify(data, null, 2) + ";\n";
fs.writeFileSync("data.js", novo, "utf8");

console.log("Cloudinary otimizado: image + thumb criados.");