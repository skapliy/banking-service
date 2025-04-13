const { defineConfig } = require('@vue/cli-service')
module.exports = {
  transpileDependencies: [],
  devServer: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
}
