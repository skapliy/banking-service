<template>
  <div>
    <h1>{{ message }}</h1>
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      message: '',
    };
  },
  async created() {
    const response = await axios.get('http://localhost:8000/');
    this.message = response.data.message;
  },
};
</script>