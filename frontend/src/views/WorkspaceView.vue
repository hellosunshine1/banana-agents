<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { cancelJob, getJob, getProject, type Job, type Project } from "../api/client";

const route = useRoute();
const project = ref<Project | null>(null);
const error = ref("");
const jobId = ref("");
const job = ref<Job | null>(null);
const jobMsg = ref("");

async function load() {
  const id = Number(route.params.id);
  project.value = await getProject(id);
}

async function fetchJob() {
  jobMsg.value = "";
  error.value = "";
  try {
    job.value = await getJob(Number(jobId.value));
  } catch (e) {
    error.value = e instanceof Error ? e.message : "查询 Job 失败";
  }
}

async function onCancelJob() {
  jobMsg.value = "";
  error.value = "";
  try {
    job.value = await cancelJob(Number(jobId.value));
    jobMsg.value = "已取消";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "取消失败";
  }
}

onMounted(async () => {
  try {
    await load();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载失败";
  }
});
</script>

<template>
  <div v-if="project">
    <h1>{{ project.name }}</h1>
    <p class="muted">工作台壳（M1）：参数展示；生成能力在 M2。</p>
    <p v-if="error" class="error">{{ error }}</p>

    <section class="card">
      <h2>项目参数</h2>
      <p><strong>主题</strong>：{{ project.topic || "—" }}</p>
      <p><strong>类型</strong>：{{ project.genre || "—" }}</p>
      <p><strong>章数</strong>：{{ project.num_chapters }} · <strong>每章字数</strong>：{{ project.word_number }}</p>
      <p><strong>状态</strong>：{{ project.status }}</p>
    </section>

    <section class="card">
      <h2>生成步骤（占位）</h2>
      <div class="row">
        <button class="btn" type="button" disabled>Step1 生成设定</button>
        <button class="btn" type="button" disabled>Step2 生成目录</button>
        <button class="btn" type="button" disabled>Step3 章节草稿</button>
        <button class="btn" type="button" disabled>Step4 定稿</button>
      </div>
      <p class="muted" style="margin-top: 0.75rem">将在 M2 接通 Dify / SSE / RAG。</p>
    </section>

    <section class="card">
      <h2>Job 壳（验收用）</h2>
      <p class="muted">种子会创建一条 pending Job，可在此查询/取消。</p>
      <div class="row">
        <input v-model="jobId" placeholder="job_id" style="max-width: 160px" />
        <button class="btn secondary" type="button" @click="fetchJob">查询</button>
        <button class="btn secondary" type="button" @click="onCancelJob">取消</button>
      </div>
      <p v-if="jobMsg">{{ jobMsg }}</p>
      <pre v-if="job" style="white-space: pre-wrap">{{ job }}</pre>
    </section>
  </div>
</template>
