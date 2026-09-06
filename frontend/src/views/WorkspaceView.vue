<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
  agentChat,
  cancelJob,
  consistencyCheck,
  finalizeChapter,
  generateArchitecture,
  generateBlueprint,
  getBlueprint,
  getChapter,
  getProject,
  listAudits,
  listReviews,
  pollJobUntilDone,
  putBlueprint,
  putChapter,
  streamChapterDraft,
  updateProject,
  type AgentChatResponse,
  type AuditLog,
  type BlueprintItem,
  type ConsistencyReview,
  type Job,
  type Project,
} from "../api/client";

const route = useRoute();
const projectId = computed(() => Number(route.params.id));

const tab = ref<
  "params" | "arch" | "blueprint" | "chapter" | "state" | "review" | "agent" | "audits" | "job"
>("params");
const project = ref<Project | null>(null);
const error = ref("");
const message = ref("");
const busy = ref(false);

const architecture = ref("");
const characterState = ref("");
const globalSummary = ref("");

const blueprints = ref<BlueprintItem[]>([]);
const chapterNum = ref(1);
const chapterContent = ref("");
const chapterStatus = ref("empty");
const guidance = ref("");
const draftAbort = ref<AbortController | null>(null);

const activeJobId = ref<number | null>(null);
const activeJob = ref<Job | null>(null);
let pollStop = false;

const reviews = ref<ConsistencyReview[]>([]);
const agentInput = ref("");
const agentHistory = ref<AgentChatResponse[]>([]);
const audits = ref<AuditLog[]>([]);

async function reloadProject() {
  project.value = await getProject(projectId.value);
  architecture.value = project.value.architecture || "";
  characterState.value = project.value.character_state || "";
  globalSummary.value = project.value.global_summary || "";
}

async function reloadBlueprint() {
  const res = await getBlueprint(projectId.value);
  blueprints.value = res.items;
}

async function reloadChapter() {
  const ch = await getChapter(projectId.value, chapterNum.value);
  chapterContent.value = ch.content || "";
  chapterStatus.value = ch.status;
}

async function reloadReviews() {
  reviews.value = await listReviews(projectId.value, chapterNum.value);
}

async function reloadAudits() {
  audits.value = await listAudits(projectId.value);
}

async function trackJob(jobId: number, switchToJob = true) {
  activeJobId.value = jobId;
  pollStop = false;
  if (switchToJob) tab.value = "job";
  const job = await pollJobUntilDone(jobId, (j) => {
    if (!pollStop) activeJob.value = j;
  });
  activeJob.value = job;
  if (job.status === "succeeded") {
    message.value = `Job #${jobId} 成功`;
    await reloadProject();
    if (job.type === "blueprint") await reloadBlueprint();
    if (job.type === "finalize") await reloadChapter();
    if (job.type === "consistency") {
      await reloadReviews();
      tab.value = "review";
    }
  } else if (job.status === "failed") {
    error.value = job.error || `Job #${jobId} 失败`;
  }
}

async function onGenerateArchitecture() {
  error.value = "";
  message.value = "";
  busy.value = true;
  try {
    const { job_id } = await generateArchitecture(projectId.value);
    await trackJob(job_id);
    architecture.value = (await getProject(projectId.value)).architecture;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "生成设定失败";
  } finally {
    busy.value = false;
  }
}

async function onSaveArchitecture() {
  error.value = "";
  try {
    await updateProject(projectId.value, { architecture: architecture.value });
    message.value = "设定已保存";
    await reloadProject();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "保存失败";
  }
}

async function onGenerateBlueprint() {
  error.value = "";
  message.value = "";
  busy.value = true;
  try {
    const { job_id } = await generateBlueprint(projectId.value);
    await trackJob(job_id);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "生成目录失败";
  } finally {
    busy.value = false;
  }
}

async function onSaveBlueprint() {
  error.value = "";
  try {
    const res = await putBlueprint(projectId.value, blueprints.value);
    blueprints.value = res.items;
    message.value = "目录已保存";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "保存目录失败";
  }
}

async function onStartDraft(extraGuidance?: string) {
  error.value = "";
  message.value = "";
  draftAbort.value?.abort();
  const ac = new AbortController();
  draftAbort.value = ac;
  chapterContent.value = "";
  chapterStatus.value = "drafting";
  busy.value = true;
  tab.value = "chapter";
  try {
    await streamChapterDraft(
      projectId.value,
      chapterNum.value,
      extraGuidance ?? guidance.value,
      {
        onToken: (t) => {
          chapterContent.value += t;
        },
        onError: (m) => {
          error.value = m;
        },
        onDone: () => {
          message.value = "草稿流式完成（已尝试保存）";
        },
      },
      ac.signal,
    );
    await reloadChapter();
  } catch (e) {
    if ((e as Error).name !== "AbortError") {
      error.value = e instanceof Error ? e.message : "草稿失败";
    } else {
      message.value = "已中断，保留已生成文本";
    }
  } finally {
    busy.value = false;
    draftAbort.value = null;
  }
}

function onStopDraft() {
  draftAbort.value?.abort();
}

async function onSaveChapter() {
  error.value = "";
  try {
    const ch = await putChapter(projectId.value, chapterNum.value, chapterContent.value);
    chapterStatus.value = ch.status;
    message.value = "章节已保存（未写向量）";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "保存章节失败";
  }
}

async function onFinalize() {
  error.value = "";
  message.value = "";
  busy.value = true;
  try {
    const { job_id } = await finalizeChapter(projectId.value, chapterNum.value);
    await trackJob(job_id);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "定稿失败";
  } finally {
    busy.value = false;
  }
}

async function onConsistencyCheck() {
  error.value = "";
  message.value = "";
  busy.value = true;
  try {
    const { job_id } = await consistencyCheck(projectId.value, chapterNum.value);
    await trackJob(job_id);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "审校失败";
  } finally {
    busy.value = false;
  }
}

async function onAgentSend() {
  error.value = "";
  if (!agentInput.value.trim()) return;
  busy.value = true;
  try {
    const res = await agentChat(projectId.value, {
      message: agentInput.value,
      chapter_number: chapterNum.value,
      guidance: guidance.value || undefined,
    });
    agentHistory.value.unshift(res);
    agentInput.value = "";
    if (res.job_id) {
      await trackJob(res.job_id, false);
    }
    if (res.sse_endpoint) {
      const n = Number((res.data as { chapter_number?: number } | null)?.chapter_number || chapterNum.value);
      const g = String((res.data as { guidance?: string } | null)?.guidance || guidance.value || "");
      chapterNum.value = n;
      guidance.value = g;
      await onStartDraft(g);
    }
    await reloadAudits();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Agent 调用失败";
  } finally {
    busy.value = false;
  }
}

async function onSaveState() {
  error.value = "";
  try {
    await updateProject(projectId.value, {
      character_state: characterState.value,
      global_summary: globalSummary.value,
    });
    message.value = "角色/摘要已保存";
    await reloadProject();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "保存失败";
  }
}

async function onCancelJob() {
  if (!activeJobId.value) return;
  try {
    activeJob.value = await cancelJob(activeJobId.value);
    message.value = "已请求取消";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "取消失败";
  }
}

async function onSaveParams() {
  if (!project.value) return;
  error.value = "";
  try {
    project.value = await updateProject(projectId.value, {
      name: project.value.name,
      topic: project.value.topic,
      genre: project.value.genre,
      num_chapters: project.value.num_chapters,
      word_number: project.value.word_number,
    });
    message.value = "参数已保存";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "保存失败";
  }
}

watch(chapterNum, async () => {
  try {
    await reloadChapter();
    if (tab.value === "review") await reloadReviews();
  } catch {
    /* ignore */
  }
});

onMounted(async () => {
  try {
    await reloadProject();
    await reloadBlueprint();
    await reloadChapter();
    await reloadReviews();
    await reloadAudits();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载失败";
  }
});

onUnmounted(() => {
  pollStop = true;
  draftAbort.value?.abort();
});
</script>

<template>
  <div v-if="project">
    <h1>{{ project.name }}</h1>
    <p class="muted">工作台 · 设定 → 目录 → SSE 草稿 → 定稿 · 审校 · Agent</p>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="message">{{ message }}</p>

    <div class="row" style="margin-bottom: 1rem">
      <button class="btn secondary" type="button" @click="tab = 'params'">参数</button>
      <button class="btn secondary" type="button" @click="tab = 'arch'">设定</button>
      <button class="btn secondary" type="button" @click="tab = 'blueprint'">目录</button>
      <button class="btn secondary" type="button" @click="tab = 'chapter'">章节</button>
      <button class="btn secondary" type="button" @click="tab = 'state'">角色/摘要</button>
      <button class="btn secondary" type="button" @click="tab = 'review'">审校</button>
      <button class="btn secondary" type="button" @click="tab = 'agent'">Agent</button>
      <button class="btn secondary" type="button" @click="tab = 'audits'">审计</button>
      <button class="btn secondary" type="button" @click="tab = 'job'">Job</button>
    </div>

    <section v-if="tab === 'params'" class="card">
      <h2>项目参数</h2>
      <label>名称 <input v-model="project.name" /></label>
      <label>主题 <input v-model="project.topic" /></label>
      <label>类型 <input v-model="project.genre" /></label>
      <div class="row">
        <label style="flex: 1">章数 <input v-model.number="project.num_chapters" type="number" min="0" /></label>
        <label style="flex: 1">每章字数 <input v-model.number="project.word_number" type="number" min="0" /></label>
      </div>
      <button class="btn" type="button" @click="onSaveParams">保存参数</button>
    </section>

    <section v-else-if="tab === 'arch'" class="card">
      <h2>设定</h2>
      <div class="row" style="margin-bottom: 0.75rem">
        <button class="btn" type="button" :disabled="busy" @click="onGenerateArchitecture">生成设定</button>
        <button class="btn secondary" type="button" @click="onSaveArchitecture">保存</button>
      </div>
      <textarea v-model="architecture" style="min-height: 320px" />
    </section>

    <section v-else-if="tab === 'blueprint'" class="card">
      <h2>目录</h2>
      <div class="row" style="margin-bottom: 0.75rem">
        <button class="btn" type="button" :disabled="busy" @click="onGenerateBlueprint">生成目录</button>
        <button class="btn secondary" type="button" @click="onSaveBlueprint">保存目录</button>
        <button class="btn secondary" type="button" @click="reloadBlueprint">刷新</button>
      </div>
      <div v-for="(item, idx) in blueprints" :key="item.chapter_number" class="card" style="background: #faf8f4">
        <strong>第 {{ item.chapter_number }} 章</strong>
        <label>标题 <input v-model="blueprints[idx].title" /></label>
        <label>概要 <textarea v-model="blueprints[idx].summary" style="min-height: 80px" /></label>
      </div>
      <p v-if="!blueprints.length" class="muted">暂无目录，请先生成。</p>
    </section>

    <section v-else-if="tab === 'chapter'" class="card">
      <h2>章节草稿</h2>
      <div class="row">
        <label style="max-width: 140px">章号 <input v-model.number="chapterNum" type="number" min="1" /></label>
        <span class="muted">状态：{{ chapterStatus }}</span>
      </div>
      <label>本章指导 <input v-model="guidance" placeholder="可选" /></label>
      <div class="row" style="margin: 0.75rem 0">
        <button class="btn" type="button" :disabled="busy" @click="onStartDraft()">SSE 生成草稿</button>
        <button class="btn secondary" type="button" @click="onStopDraft">中断</button>
        <button class="btn secondary" type="button" @click="onSaveChapter">保存草稿</button>
        <button class="btn" type="button" :disabled="busy" @click="onFinalize">定稿</button>
      </div>
      <textarea v-model="chapterContent" style="min-height: 360px" />
    </section>

    <section v-else-if="tab === 'state'" class="card">
      <h2>角色状态 / 全局摘要</h2>
      <label>角色状态 <textarea v-model="characterState" style="min-height: 160px" /></label>
      <label>全局摘要 <textarea v-model="globalSummary" style="min-height: 160px" /></label>
      <button class="btn" type="button" @click="onSaveState">保存</button>
    </section>

    <section v-else-if="tab === 'review'" class="card">
      <h2>一致性审校</h2>
      <p class="muted">只展示冲突，不自动改文。请先有章节正文。</p>
      <div class="row" style="margin-bottom: 0.75rem">
        <label style="max-width: 140px">章号 <input v-model.number="chapterNum" type="number" min="1" /></label>
        <button class="btn" type="button" :disabled="busy" @click="onConsistencyCheck">发起审校</button>
        <button class="btn secondary" type="button" @click="reloadReviews">刷新结果</button>
      </div>
      <div v-for="rev in reviews" :key="rev.id" class="card" style="background: #faf8f4">
        <p class="muted">#{{ rev.id }} · {{ rev.created_at }} · job {{ rev.job_id ?? "—" }}</p>
        <p v-if="rev.conflicts?.summary"><strong>摘要：</strong>{{ rev.conflicts.summary }}</p>
        <ul v-if="rev.conflicts?.conflicts?.length">
          <li v-for="(c, i) in rev.conflicts.conflicts" :key="i">
            <strong>{{ c.type || "conflict" }}</strong>
            <span v-if="c.severity"> [{{ c.severity }}]</span>
            — {{ c.detail }}
          </li>
        </ul>
        <p v-else class="muted">无结构化冲突条目</p>
      </div>
      <p v-if="!reviews.length" class="muted">暂无审校记录</p>
    </section>

    <section v-else-if="tab === 'agent'" class="card">
      <h2>受控 Agent</h2>
      <p class="muted">仅返回 JSON；草稿意图返回 SSE 端点后由前端拉流。</p>
      <label>
        指令
        <input v-model="agentInput" placeholder="例如：生成设定 / 审校第1章 / 检索废土" @keyup.enter="onAgentSend" />
      </label>
      <button class="btn" type="button" :disabled="busy" @click="onAgentSend">发送</button>
      <div v-for="(item, idx) in agentHistory" :key="idx" class="card" style="margin-top: 0.75rem; background: #faf8f4">
        <pre style="white-space: pre-wrap; margin: 0">{{ item }}</pre>
      </div>
    </section>

    <section v-else-if="tab === 'audits'" class="card">
      <h2>Agent 审计</h2>
      <button class="btn secondary" type="button" @click="reloadAudits">刷新</button>
      <table class="table" v-if="audits.length">
        <thead>
          <tr>
            <th>ID</th>
            <th>意图</th>
            <th>工具</th>
            <th>状态</th>
            <th>摘要</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in audits" :key="a.id">
            <td>{{ a.id }}</td>
            <td>{{ a.intent }}</td>
            <td>{{ a.tool_name || "—" }}</td>
            <td>{{ a.status }}</td>
            <td>{{ a.result_summary }}</td>
          </tr>
        </tbody>
      </table>
      <p v-else class="muted">暂无审计</p>
    </section>

    <section v-else class="card">
      <h2>Job 进度</h2>
      <p class="muted">最近任务：{{ activeJobId ?? "无" }}</p>
      <div class="row">
        <button class="btn secondary" type="button" :disabled="!activeJobId" @click="onCancelJob">取消当前 Job</button>
      </div>
      <pre v-if="activeJob" style="white-space: pre-wrap">{{ activeJob }}</pre>
    </section>
  </div>
</template>
