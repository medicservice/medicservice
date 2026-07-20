(function (global) {
  var PHOTOS = {
    Usai: "usai.webp",
    Cabula: "Cabula.webp",
    Cadeddu: "Cadeddu.webp",
    Canu: "Canu.webp",
    CartaGabriele: "gabrielecarta.webp",
    Carta: "brunocarta.webp",
    Corona: "corona.webp",
    Diana: "diana.webp",
    Oppo: "oppo.webp",
    Paderi: "paderi.webp",
    Pibi: "pibi.webp",
    Picciau: "picciau.webp",
    Pintor: "pintor.webp",
    Pitzalis: "pitzalis.webp",
    Salfi: "salfi.webp",
    Trincas: "Trincas.webp",
    Concas: "concas.webp",
    Fornero: "fornero.webp",
    Humaidan: "humaidan.webp",
    Maleddu: "maleddu.webp",
    Melis: "melis.webp",
    Monni: "monni.webp",
    Mirai: "mirai.webp",
  };

  function isFemaleDoctor(display) {
    return /^(Dr\.ssa|Op\.)\b/i.test(display || "");
  }

  function doctorPhotoSrc(surname, display, prefix) {
    prefix = prefix || "assets/photos/";
    var file = PHOTOS[surname];
    if (file) return prefix + file;
    return prefix + (isFemaleDoctor(display) ? "generic_medic_female.png" : "generic_medic_male.png");
  }

  global.doctorPhotoSrc = doctorPhotoSrc;
  global.isFemaleDoctor = isFemaleDoctor;
})((typeof window !== "undefined" && window) || globalThis);
