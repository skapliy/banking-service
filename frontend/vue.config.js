const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true, // Оставьте эту строку, если она нужна вашему проекту
  devServer: {
    allowedHosts: 'all', // Разрешает доступ с любого хоста
  }
})
