// docmd.config.js
export default defineConfig({
  // --- Core Metadata ---
  title: 'Spark CLI',
  url: 'https://variableway.github.io/spark-cli',

  // --- Source & Output ---
  src: 'docs',
  out: 'site',

  // --- Layout & UI Architecture ---
  layout: {
    spa: true,
    header: {
      enabled: true,
    },
    sidebar: {
      collapsible: true,
      defaultCollapsed: false,
    },
    optionsMenu: {
      position: 'sidebar-top',
      components: {
        search: true,
        themeSwitch: true,
        sponsor: null,
      },
    },
    footer: {
      style: 'minimal',
      content: '© ' + new Date().getFullYear() + ' Spark CLI',
      branding: true,
    },
  },

  // --- Theme Settings ---
  theme: {
    name: 'sky',
    appearance: 'system',
    codeHighlight: true,
    customCss: [],
  },

  // --- General Features ---
  minify: true,
  autoTitleFromH1: true,
  copyCode: true,
  pageNavigation: true,

  // --- Navigation (Sidebar) ---
  navigation: [
    { title: '首页', path: '/', icon: 'home' },
    {
      title: '使用指南',
      icon: 'book',
      collapsible: true,
      children: [
        { title: '概览', path: '/usage/usage' },
        { title: 'Git 管理', path: '/usage/git' },
        { title: 'AI Agent 配置', path: '/usage/agent' },
        { title: '任务管理', path: '/usage/task' },
        { title: '系统工具', path: '/usage/magic' },
        { title: '脚本管理', path: '/usage/script' },
        { title: '文档管理', path: '/usage/docs-cmd' },
      ],
    },
    {
      title: '架构设计',
      icon: 'sitemap',
      collapsible: true,
      children: [
        { title: '项目分析报告', path: '/analysis/project-analysis' },
      ],
    },
    {
      title: '功能介绍',
      icon: 'puzzle-piece',
      collapsible: true,
      children: [
        { title: 'Git 管理', path: '/features/git' },
        { title: 'Agent 配置', path: '/features/agent' },
        { title: '任务管理', path: '/features/task' },
        { title: '系统工具', path: '/features/magic' },
        { title: '脚本管理', path: '/features/script' },
        { title: '文档管理', path: '/features/docs-feature' },
      ],
    },
    {
      title: '命令规格',
      icon: 'terminal',
      collapsible: true,
      children: [
        { title: 'Git', path: '/spec/git' },
        { title: 'Agent', path: '/spec/agent' },
        { title: 'Task', path: '/spec/task' },
        { title: 'Magic', path: '/spec/magic' },
        { title: 'Script', path: '/spec/script' },
        { title: 'Docs', path: '/spec/docs-cmd' },
      ],
    },
    { title: 'Agents', path: '/Agents', icon: 'robot' },
  ],

  // --- Plugins ---
  plugins: {
    seo: {
      defaultDescription: '管理多个 Git 仓库的 CLI 工具',
      openGraph: { defaultImage: '' },
      twitter: { cardType: 'summary_large_image' },
    },
    sitemap: { defaultChangefreq: 'weekly' },
    search: {},
    mermaid: {},
    llms: { fullContext: true },
  },

  // --- Edit Link ---
  editLink: {
    enabled: true,
    baseUrl: 'https://github.com/variableway/spark-cli/edit/main/docs',
    text: '编辑此页',
  },
});
