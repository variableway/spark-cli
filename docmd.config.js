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
        { title: 'Git 仓库更新', path: '/usage/update' },
        { title: 'Mono-repo 创建', path: '/usage/create' },
        { title: '子模块同步', path: '/usage/sync' },
        { title: 'Gitcode 远程', path: '/usage/gitcode' },
        { title: '任务管理', path: '/usage/task' },
        { title: 'AI Agent 配置', path: '/usage/agent' },
        { title: 'VS Code 配置', path: '/usage/vscode-setup' },
      ],
    },
    {
      title: '架构设计',
      icon: 'sitemap',
      collapsible: true,
      children: [
        { title: 'CLI 集成报告', path: '/analysis/cli-integration-report' },
        { title: 'Spark Hub 架构 RFC', path: '/analysis/spark-hub-architecture-rfc' },
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
