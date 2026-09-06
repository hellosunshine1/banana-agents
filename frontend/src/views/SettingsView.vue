<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { getSettings, getUser, putSettings, type AppSettings } from "../api/client";

const settings = ref<AppSettings | null>(null);
const llmText = ref("");
const embeddingText = ref("");
const chooseText = ref("");
const error = ref("");
const message = ref("");
const user = computed(() => getUser());
const isAdmin = computed(() => Boolean(user.value?.is_admin));

function loadIntoEditors(data: AppSettings) {
  settings.value = data;
  llmText.value = JSON.stringify(data.llm_configs, null, 2);
  embeddingText.value = JSON.stringify(data.embedding_configs, null, 2);
  chooseText.value = JSON.stringify(data.choose_configs, null, 2);
}

async function refresh() {
  const data = await getSettings();
  loadIntoEditors(data);
}

async function onSave() {
  error.value = "";
  message.value = "";
  try {
    const payload = {
      llm_configs: JSON.parse(llmText.value),
      embedding_configs: JSON.parse(embeddingText.value),
      choose_configs: JSON.parse(chooseText.value),
    };
    const data = await putSettings(payload);
    loadIntoEditors(data);
    message.value = "已保存";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "保存失败";
  }
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
    <h1>全局设置</h1>
    <p class="muted">维护 llm / embedding / choose_configs。Dify 与 Job 超时等运维项不在此页。</p>
    <p v-if="!isAdmin" class="muted">当前账号非 admin，仅可查看。</p>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="message">{{ message }}</p>

    <section class="card" v-if="settings">
      <label>
        llm_configs
        <textarea v-model="llmText" :readonly="!isAdmin" />
      </label>
      <label>
        embedding_configs
        <textarea v-model="embeddingText" :readonly="!isAdmin" />
      </label>
      <label>
        choose_configs
        <textarea v-model="chooseText" :readonly="!isAdmin" />
      </label>
      <button class="btn" type="button" :disabled="!isAdmin" @click="onSave">保存</button>
    </section>
  </div>
</template>
