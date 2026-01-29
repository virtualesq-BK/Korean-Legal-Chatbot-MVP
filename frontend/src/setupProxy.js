const { createProxyMiddleware } = require('http-proxy-middleware');

/**
 * Proxy only backend API paths to avoid ECONNREFUSED for /favicon.ico etc.
 * when the backend (port 8000) is not running.
 */
module.exports = function (app) {
  app.use(
    createProxyMiddleware(
      ['/chat', '/health', '/countries', '/english-laws', '/laws'],
      {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    )
  );
};
