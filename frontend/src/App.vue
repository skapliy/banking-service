<template>
  <div id="app">
    <header>
    </header>
    <main>
      <AccountList />
    </main>
  </div>
</template>

<script>
import AccountList from './components/AccountList.vue'

export default {
  name: 'App',
  components: {
    AccountList
  }
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
  margin: 0;
  padding: 0;
}

header {
  background-color: #f8f9fa;
  padding: 1px;
  text-align: center;
  box-shadow: 0 0px 0px rgba(0, 0, 0, 0.1);
}

main {
  padding: 10px;
  max-width: 1200px;
  margin: 0 auto;
}
</style>