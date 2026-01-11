// /** @type {import('@prisma/internals').ConfigWithPath} */
// export default {
//   datasource: {

//     db: {
//       provider: "postgresql",
//       url: process.env.DATABASE_URL,
//     },

//   },
// };
// const { defineConfig } = require("@prisma/config");

// module.exports = defineConfig({
//   datasource: {
//     db: {
//       provider: "postgresql",
//       url: process.env.DATABASE_URL,
//     },
//   },
// });
// require("dotenv/config"); // ✅ BẮT BUỘC
const dotenv = require("dotenv");
dotenv.config();
const { defineConfig } = require("@prisma/config");

module.exports = defineConfig({
  datasource: {
    url: process.env.DATABASE_URL, // ✅ CHUẨN
  },
});
