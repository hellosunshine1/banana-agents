<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { clearAuth, getUser, isLoggedIn } from "./api/client";

const router = useRouter();
const route = useRoute();
const loggedIn = computed(() => {
  void route.fullPath;
  return isLoggedIn();
});
const user = computed(() => {
  void route.fullPath;
  return getUser();
});

function logout() {
  clearAuth();
  router.push({ name: "login" });
}
</script>

<template>
  <div>
    <header class="nav" v-if="loggedIn">
      <strong>Banana Agents</strong>
      <router-link to="/projects">项目</router-link>
      <router-link to="/settings">设置</router-link>
      <span class="muted" style="margin-left: auto">{{ user?.username }}</span>
      <button class="btn secondary" type="button" @click="logout">退出</button>
    </header>
    <main class="container">
      <router-view />
    </main>
  </div>
</template>
