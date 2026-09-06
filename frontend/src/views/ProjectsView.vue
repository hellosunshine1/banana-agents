<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { createProject, deleteProject, listProjects, type Project } from "../api/client";

const router = useRouter();
const projects = ref<Project[]>([]);
const error = ref("");
const form = reactive({
  name: "",
  topic: "",
  genre: "",
  num_chapters: 10,
  word_number: 3000,
});

async function refresh() {
  projects.value = await listProjects();
}

async function onCreate() {
  error.value = "";
  try {
    await createProject({ ...form });
    form.name = "";
    form.topic = "";
    form.genre = "";
    await refresh();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "创建失败";
  }
}

async function onDelete(id: number) {
  if (!confirm("确认删除该项目？")) return;
  await deleteProject(id);
  await refresh();
}

onMounted(async () => {
  try {
    await refresh();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载失败";
  }
});
</script>

<template>
  <div>
    <h1>项目</h1>
    <p v-if="error" class="error">{{ error }}</p>

    <section class="card">
      <h2>新建项目</h2>
      <form @submit.prevent="onCreate">
        <label>名称 <input v-model="form.name" required /></label>
        <label>主题 <input v-model="form.topic" /></label>
        <label>类型 <input v-model="form.genre" /></label>
        <div class="row">
          <label style="flex: 1">章数 <input v-model.number="form.num_chapters" type="number" min="0" /></label>
          <label style="flex: 1">每章字数 <input v-model.number="form.word_number" type="number" min="0" /></label>
        </div>
        <button class="btn" type="submit">创建</button>
      </form>
    </section>

    <section class="card">
      <h2>我的项目</h2>
      <table class="table" v-if="projects.length">
        <thead>
          <tr>
            <th>ID</th>
            <th>名称</th>
            <th>主题</th>
            <th>章数</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in projects" :key="p.id">
            <td>{{ p.id }}</td>
            <td>{{ p.name }}</td>
            <td>{{ p.topic || "—" }}</td>
            <td>{{ p.num_chapters }}</td>
            <td class="row">
              <button class="btn secondary" type="button" @click="router.push(`/projects/${p.id}`)">打开</button>
              <button class="btn secondary" type="button" @click="onDelete(p.id)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="muted">暂无项目</p>
    </section>
  </div>
</template>
