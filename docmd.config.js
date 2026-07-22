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

  // --- Internationalization ---
  // Default locale (zh) renders at site root; English mirror lives under /en/.
  // Navigation labels are sourced from per-locale navigation.json files
  // (docs/zh/navigation.json and docs/en/navigation.json).
  i18n: {
    default: 'zh',
    position: 'options-menu',
    locales: [
      {
        id: 'zh',
        label: '简体中文',
        dir: 'ltr',
        translations: { editLinkText: '编辑此页' },
      },
      {
        id: 'en',
        label: 'English',
        dir: 'ltr',
        translations: { editLinkText: 'Edit this page' },
      },
    ],
  },

  // --- Plugins ---
  plugins: {
    seo: {
      defaultDescription: 'Spark CLI — daily dev automation and AI skill integration',
      openGraph: { defaultImage: '' },
      twitter: { cardType: 'summary_large_image' },
    },
    sitemap: { defaultChangefreq: 'weekly' },
    search: {},
    mermaid: {},
    llms: { fullContext: true },
  },

  // --- Edit Link ---
  // baseUrl always points at the default locale directory on disk so the
  // "Edit this page" link resolves to a real file in docs/zh/.
  editLink: {
    enabled: true,
    baseUrl: 'https://github.com/variableway/spark-cli/edit/main/docs/zh',
  },
});
