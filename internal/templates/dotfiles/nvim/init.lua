--[[
  Spark CLI bundled Nvim template
  Copy this to ~/.config/nvim/ and customize to your needs.

  Usage:
    spark magic copy-config ~/dotfiles/
    spark magic copy-config user@192.168.1.100:~/dotfiles/
]]

-- Bootstrap lazy.nvim
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
  vim.fn.system({
    "git",
    "clone",
    "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git",
    "--branch=stable",
    lazypath,
  })
end
vim.opt.rtp:prepend(lazypath)

-- Basic options
vim.opt.number = true
vim.opt.relativenumber = true
vim.opt.tabstop = 2
vim.opt.shiftwidth = 2
vim.opt.expandtab = true
vim.opt.mouse = "a"
vim.opt.termguicolors = true
vim.opt.clipboard = "unnamedplus"
vim.opt.ignorecase = true
vim.opt.smartcase = true
vim.opt.splitright = true
vim.opt.splitbelow = true

-- Keymaps
local map = vim.keymap.set
map("n", "<Esc>", "<cmd>nohlsearch<CR>", { desc = "Clear search highlight" })
map("n", "<C-h>", "<C-w>h", { desc = "Go to left window" })
map("n", "<C-l>", "<C-w>l", { desc = "Go to right window" })
map("n", "<C-j>", "<C-w>j", { desc = "Go to lower window" })
map("n", "<C-k>", "<C-w>k", { desc = "Go to upper window" })

-- Plugins
require("lazy").setup({
  -- Colorscheme
  { "shaunsingh/nord.nvim", priority = 1000, config = function()
    vim.cmd.colorscheme("nord")
  end },

  -- Statusline
  { "nvim-lualine/lualine.nvim", event = "VeryLazy", opts = {} },
})
