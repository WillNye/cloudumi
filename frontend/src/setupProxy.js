// setupProxy.js doesn't need to be imported anywhere. It's automatically
// used for dev requests

const proxy = require("http-proxy-middleware");

module.exports = function (app) {
  app.use(
    proxy("/auth", {
      target: "http://localhost:8092",
      changeOrigin: false,
    })
  );
  app.use(
    proxy("/noauth", {
      target: "http://localhost:8092",
      changeOrigin: false,
    })
  );
  app.use(
    proxy("/saml", {
      target: "http://localhost:8092",
      changeOrigin: false,
    })
  );
  app.use(
    proxy("/noauth", {
      target: "http://localhost:8092",
      changeOrigin: false,
    })
  );
  app.use(
    proxy("/api", {
      target: "http://localhost:8092",
      changeOrigin: false,
    })
  );
};
