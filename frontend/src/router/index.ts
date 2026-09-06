import { createRouter, createWebHistory } from "vue-router";
import { isLoggedIn } from "../api/client";
import LoginView from "../views/LoginView.vue";
import ProjectsView from "../views/ProjectsView.vue";
import SettingsView from "../views/SettingsView.vue";
import WorkspaceView from "../views/WorkspaceView.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/projects" },
    { path: "/login", name: "login", component: LoginView, meta: { public: true } },
    { path: "/projects", name: "projects", component: ProjectsView },
    { path: "/projects/:id", name: "workspace", component: WorkspaceView },
    { path: "/settings", name: "settings", component: SettingsView },
  ],
});

router.beforeEach((to) => {
  if (!to.meta.public && !isLoggedIn()) {
    return { name: "login", query: { redirect: to.fullPath } };
  }
  if (to.name === "login" && isLoggedIn()) {
    return { name: "projects" };
  }
  return true;
});
