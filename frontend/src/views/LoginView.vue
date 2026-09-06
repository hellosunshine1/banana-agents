<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { login, setAuth } from "../api/client";

const router = useRouter();
const route = useRoute();
const username = ref("admin");
const password = ref("123456");
const error = ref("");
const loading = ref(false);

async function onSubmit() {
  error.value = "";
  loading.value = true;
  try {
    const res = await login(username.value, password.value);
    setAuth(res.access_token, res.user);
    const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "/projects";
    await router.replace(redirect);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "登录失败";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div style="max-width: 420px; margin: 4rem auto">
    <h1>登录</h1>
    <p class="muted">种子账号 admin / 123456</p>
    <form class="card" @submit.prevent="onSubmit">
      <label>
        用户名
        <input v-model="username" autocomplete="username" required />
      </label>
      <label>
        密码
        <input v-model="password" type="password" autocomplete="current-password" required />
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <button class="btn" type="submit" :disabled="loading">
        {{ loading ? "登录中…" : "登录" }}
      </button>
    </form>
  </div>
</template>
