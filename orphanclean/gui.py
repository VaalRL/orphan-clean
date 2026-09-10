#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
orphan-clean: Web GUI Dashboard Server
Author: Knowledge-trend-research
License: MIT
"""

import os
import sys
import json
import base64
import threading
import webbrowser
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

try:
    from .core import LocalDependencyMatcher, normalize_name, CORE_PROTECTED_PACKAGES
except (ImportError, ValueError):
    try:
        from core import LocalDependencyMatcher, normalize_name, CORE_PROTECTED_PACKAGES
    except ImportError:
        from orphanclean.core import LocalDependencyMatcher, normalize_name, CORE_PROTECTED_PACKAGES

# Global matcher instance
CURRENT_MATCHER: Optional[LocalDependencyMatcher] = None

HTML_PAGE = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>orphan-clean Dashboard</title>
  <link rel="icon" type="image/png" href="data:image/png;base64,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">
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: #111827;
      --card-border: #1f2937;
      --text: #f3f4f6;
      --text-muted: #9ca3af;
      --emerald: #10b981;
      --emerald-glow: rgba(16, 185, 129, 0.2);
      --cyan: #06b6d4;
      --amber: #f59e0b;
      --rose: #f43f5e;
      --indigo: #6366f1;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background: var(--bg); color: var(--text); padding: 24px; min-height: 100vh; }
    
    .header { display: flex; align-items: center; justify-content: space-between; padding-bottom: 20px; border-bottom: 1px solid var(--card-border); margin-bottom: 24px; }
    .brand { display: flex; align-items: center; gap: 14px; }
    .brand img { width: 44px; height: 44px; border-radius: 10px; box-shadow: 0 0 15px var(--emerald-glow); }
    .brand h1 { font-size: 22px; font-weight: 700; background: linear-gradient(90deg, #10b981, #06b6d4); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .version-tag { font-size: 11px; padding: 2px 8px; border-radius: 12px; background: #1e293b; color: var(--cyan); border: 1px solid #334155; }
    
    .search-bar { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 16px; margin-bottom: 24px; display: flex; gap: 12px; align-items: center; }
    .search-input { flex: 1; background: #0b0f19; border: 1px solid #374151; border-radius: 8px; padding: 10px 14px; color: var(--text); font-size: 14px; outline: none; }
    .search-input:focus { border-color: var(--emerald); }
    .btn { background: #1f2937; color: var(--text); border: 1px solid #374151; padding: 10px 18px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px; }
    .btn:hover { background: #374151; }
    .btn-primary { background: linear-gradient(135deg, #10b981, #059669); border: none; color: #fff; box-shadow: 0 0 12px var(--emerald-glow); }
    .btn-primary:hover { opacity: 0.9; }
    .btn-danger { background: linear-gradient(135deg, #f43f5e, #e11d48); border: none; color: #fff; }
    .btn-danger:hover { opacity: 0.9; }

    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .stat-card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 16px; }
    .stat-title { font-size: 12px; color: var(--text-muted); text-transform: uppercase; font-weight: 600; margin-bottom: 6px; }
    .stat-value { font-size: 26px; font-weight: 700; color: var(--text); }
    .stat-value.emerald { color: var(--emerald); }
    .stat-value.amber { color: var(--amber); }
    .stat-value.cyan { color: var(--cyan); }

    .tabs { display: flex; gap: 8px; border-bottom: 1px solid var(--card-border); margin-bottom: 20px; }
    .tab { padding: 10px 18px; cursor: pointer; font-size: 14px; font-weight: 600; color: var(--text-muted); border-bottom: 2px solid transparent; transition: all 0.2s; }
    .tab:hover { color: var(--text); }
    .tab.active { color: var(--emerald); border-bottom-color: var(--emerald); }

    .tab-content { display: none; }
    .tab-content.active { display: block; }

    .panel { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 20px; }
    .action-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px; }
    .filter-tags { display: flex; gap: 8px; }
    .tag-btn { padding: 6px 12px; border-radius: 6px; font-size: 12px; border: 1px solid var(--card-border); background: #0b0f19; color: var(--text-muted); cursor: pointer; }
    .tag-btn.active { background: #1e293b; color: var(--emerald); border-color: var(--emerald); }

    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th { text-align: left; padding: 12px; color: var(--text-muted); border-bottom: 1px solid var(--card-border); font-weight: 600; }
    td { padding: 12px; border-bottom: 1px solid #1a2234; vertical-align: middle; }
    tr:hover { background: #161f30; }

    .badge { display: inline-block; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
    .badge-safe { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-tool { background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-protected { background: rgba(244, 63, 94, 0.15); color: #f43f5e; border: 1px solid rgba(244, 63, 94, 0.3); }
    .badge-active { background: rgba(99, 102, 241, 0.15); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.3); }

    .modal { position: fixed; inset: 0; background: rgba(0,0,0,0.7); display: none; align-items: center; justify-content: center; z-index: 100; }
    .modal.active { display: flex; }
    .modal-box { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 24px; max-width: 500px; width: 90%; }
    .modal-box h3 { margin-bottom: 12px; }
    .modal-box p { color: var(--text-muted); font-size: 14px; margin-bottom: 20px; line-height: 1.5; }
    .modal-actions { display: flex; justify-content: flex-end; gap: 12px; }
  </style>
</head>
<body>

  <div class="header">
    <div class="brand">
      <img src="data:image/png;base64,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" alt="Logo">
      <div>
        <div style="display: flex; align-items: center; gap: 8px;">
          <h1>orphan-clean</h1>
          <span class="version-tag">v1.0.0</span>
        </div>
        <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">
          Polyglot Dependency Auditor & Safe Orphan Cleaner
        </div>
      </div>
    </div>
    <div style="display: flex; align-items: center; gap: 10px;">
      <a href="https://opensource.org/licenses/MIT" target="_blank" class="btn" style="text-decoration:none; font-size: 12px; color: #94a3b8; border-color: #334155;" title="Open Source License">
        ⚖️ MIT License
      </a>
      <a href="https://www.buymeacoffee.com/whoami885" target="_blank" class="btn" style="background: linear-gradient(135deg, #FFDD00, #FBBF24); color: #000; font-weight: 700; border: none; text-decoration: none; box-shadow: 0 0 12px rgba(251, 191, 36, 0.35);" title="Buy me a coffee (whoami885@gmail.com)">
        <img src="https://cdn.buymeacoffee.com/buttons/bmc-new-btn-logo.svg" alt="Coffee" style="width: 16px; height: 16px; vertical-align: middle;">
        Buy me a coffee
      </a>
      <a href="https://github.com/VaalRL/orphan-clean" target="_blank" class="btn" style="text-decoration:none;">
        <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/></svg>
        GitHub
      </a>
    </div>
  </div>

  <div class="search-bar">
    <span style="color: var(--text-muted); font-size: 14px; font-weight: 600;">掃描目錄：</span>
    <input type="text" id="scanPath" class="search-input" value="C:\\Users\\User\\Downloads\\Git">
    <button id="btnScan" class="btn btn-primary" onclick="startScan()">
      <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"></circle><path d="m21 21-4.3-4.3"></path></svg>
      開始審計掃描
    </button>
  </div>

  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-title">發現專案數 (Projects)</div>
      <div class="stat-value cyan" id="statProjects">0</div>
    </div>
    <div class="stat-card">
      <div class="stat-title">宣告依賴總數 (Declared)</div>
      <div class="stat-value" id="statDeclared">0</div>
    </div>
    <div class="stat-card">
      <div class="stat-title">本機 Python 安裝庫</div>
      <div class="stat-value" id="statInstalled">0</div>
    </div>
    <div class="stat-card">
      <div class="stat-title">可安全清理孤兒 (Tier 3)</div>
      <div class="stat-value emerald" id="statSafeOrphans">0</div>
    </div>
    <div class="stat-card">
      <div class="stat-title">編譯贅肉 (Build Bloat)</div>
      <div class="stat-value amber" id="statBloat">0 MB</div>
    </div>
  </div>

  <div class="tabs">
    <div class="tab active" onclick="switchTab('pythonTab', this)">🐍 Python 依賴與孤兒清理</div>
    <div class="tab" onclick="switchTab('nodeTab', this)">🌐 Node.js 專案與全域工具</div>
    <div class="tab" onclick="switchTab('bloatTab', this)">🚀 磁碟大瘦身 (Rust / Flutter)</div>
    <div class="tab" onclick="switchTab('backupTab', this)">🛡️ 備份與歷史還原清單</div>
  </div>

  <!-- TAB 1: Python -->
  <div id="pythonTab" class="tab-content active">
    <div class="panel">
      <div class="action-row">
        <div class="filter-tags">
          <button class="tag-btn active" onclick="filterPackages('safe', this)">可安全移除 (Tier 3)</button>
          <button class="tag-btn" onclick="filterPackages('tool', this)">CLI 工具 (Tier 2)</button>
          <button class="tag-btn" onclick="filterPackages('protected', this)">系統核心 (受保護)</button>
          <button class="tag-btn" onclick="filterPackages('all', this)">全部已安裝</button>
        </div>
        <div style="display: flex; gap: 8px;">
          <button class="btn" onclick="toggleSelectAll()">全選/取消</button>
          <button class="btn btn-danger" onclick="confirmClean()">
            <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M3 6h18m-2 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
            批次安全卸載所選 (<span id="selectedCount">0</span>)
          </button>
        </div>
      </div>

      <div style="max-height: 520px; overflow-y: auto;">
        <table>
          <thead>
            <tr>
              <th width="40"><input type="checkbox" id="selectAllCheckbox" onchange="toggleSelectAll(this.checked)"></th>
              <th>套件名稱 (Package)</th>
              <th>已安裝版本</th>
              <th>安全分類狀態</th>
              <th>相依關係 / 被誰引用</th>
            </tr>
          </thead>
          <tbody id="packageTableBody">
            <tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 40px;">點擊上方「開始審計掃描」以載入專案與套件矩陣</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- TAB 2: Node.js -->
  <div id="nodeTab" class="tab-content">
    <div class="panel">
      <h3 style="margin-bottom: 12px;">Node.js 專案與全域 npm 套件</h3>
      <div style="max-height: 480px; overflow-y: auto;">
        <table>
          <thead>
            <tr>
              <th>專案名稱 / 全域工具</th>
              <th>生態系</th>
              <th>環境類型</th>
              <th>路徑</th>
              <th>宣告相依數</th>
            </tr>
          </thead>
          <tbody id="nodeTableBody">
            <tr><td colspan="5" style="text-align: center; color: var(--text-muted); padding: 30px;">尚無掃描資料</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- TAB 3: Bloat -->
  <div id="bloatTab" class="tab-content">
    <div class="panel">
      <div class="action-row">
        <h3>Rust 與 Flutter 龐大建置中間檔 (target/ 與 build/)</h3>
        <button class="btn btn-danger" onclick="cleanAllBloat()">一鍵清理全部中間產物</button>
      </div>
      <div style="max-height: 480px; overflow-y: auto;">
        <table>
          <thead>
            <tr>
              <th>專案名稱</th>
              <th>生態系</th>
              <th>贅肉類型</th>
              <th>佔用空間</th>
              <th>資料夾路徑</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody id="bloatTableBody">
            <tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 30px;">尚無掃描資料</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- TAB 4: Backups -->
  <div id="backupTab" class="tab-content">
    <div class="panel">
      <div class="action-row">
        <h3>歷史備份快照 (Rollback Snapshots)</h3>
        <button class="btn" onclick="loadBackups()">重新整理備份清單</button>
      </div>
      <div style="max-height: 480px; overflow-y: auto;">
        <table>
          <thead>
            <tr>
              <th>備份檔案名稱</th>
              <th>建立時間</th>
              <th>檔案大小</th>
              <th>一鍵回滾還原指令</th>
            </tr>
          </thead>
          <tbody id="backupTableBody">
            <tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 30px;">尚無備份紀錄</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Confirmation Modal -->
  <div id="cleanModal" class="modal">
    <div class="modal-box">
      <h3>確認安全批次卸載？</h3>
      <p id="modalDesc">將自動為您執行 pip freeze 產生備份快照，隨後卸載所選的套件。</p>
      <div class="modal-actions">
        <button class="btn" onclick="closeModal()">取消</button>
        <button class="btn btn-danger" onclick="executeClean()">確認備份並卸載</button>
      </div>
    </div>
  </div>

  <script>
    let currentData = null;
    let currentFilter = 'safe';
    let selectedPackages = new Set();

    function switchTab(tabId, el) {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      el.classList.add('active');
      document.getElementById(tabId).classList.add('active');
      if (tabId === 'backupTab') loadBackups();
    }

    async function startScan() {
      const path = document.getElementById('scanPath').value;
      const btn = document.getElementById('btnScan');
      btn.innerHTML = '掃描中...';
      btn.disabled = true;

      try {
        const res = await fetch('/api/scan', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({path: path})
        });
        currentData = await res.json();
        renderDashboard();
      } catch (err) {
        alert('掃描失敗: ' + err);
      } finally {
        btn.innerHTML = '<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"></circle><path d="m21 21-4.3-4.3"></path></svg> 開始審計掃描';
        btn.disabled = false;
      }
    }

    function renderDashboard() {
      if (!currentData) return;
      document.getElementById('statProjects').innerText = currentData.projects.length;
      document.getElementById('statDeclared').innerText = currentData.orphans.declared_count;
      document.getElementById('statInstalled').innerText = currentData.orphans.total_installed;
      document.getElementById('statSafeOrphans').innerText = currentData.orphans.tier3_pure_libraries.length;
      
      let totalBloat = currentData.bloat.reduce((sum, b) => sum + (b.size_mb || 0), 0);
      document.getElementById('statBloat').innerText = totalBloat.toFixed(1) + ' MB';

      renderPackageTable();
      renderNodeTable();
      renderBloatTable();
    }

    function filterPackages(type, el) {
      currentFilter = type;
      document.querySelectorAll('.filter-tags .tag-btn').forEach(b => b.classList.remove('active'));
      el.classList.add('active');
      renderPackageTable();
    }

    function renderPackageTable() {
      if (!currentData) return;
      const tbody = document.getElementById('packageTableBody');
      tbody.innerHTML = '';

      let list = [];
      const orphans = currentData.orphans;

      if (currentFilter === 'safe') {
        list = orphans.tier3_pure_libraries.map(p => ({...p, tag: 'safe', label: '可安全移除 (Tier 3)'}));
      } else if (currentFilter === 'tool') {
        list = orphans.tier2_cli_tools.map(p => ({...p, tag: 'tool', label: 'CLI 工具 (Tier 2)'}));
      } else if (currentFilter === 'protected') {
        list = orphans.tier1_protected.map(p => ({...p, tag: 'protected', label: '系統核心 (受保護)'}));
      } else {
        // all
        list = [
          ...orphans.tier3_pure_libraries.map(p => ({...p, tag: 'safe', label: '可安全移除'})),
          ...orphans.tier2_cli_tools.map(p => ({...p, tag: 'tool', label: 'CLI 工具'})),
          ...orphans.tier1_protected.map(p => ({...p, tag: 'protected', label: '受保護核心'}))
        ];
      }

      list.forEach(item => {
        const tr = document.createElement('tr');
        const isProtected = item.tag === 'protected';
        const isChecked = selectedPackages.has(item.name);

        tr.innerHTML = `
          <td><input type="checkbox" ${isProtected ? 'disabled' : ''} ${isChecked ? 'checked' : ''} onchange="toggleSelectPkg('${item.name}', this.checked)"></td>
          <td style="font-weight: 600; color: ${item.tag === 'safe' ? '#34d399' : 'inherit'};">${item.name}</td>
          <td style="color: var(--text-muted);">${item.version}</td>
          <td><span class="badge badge-${item.tag}">${item.label}</span></td>
          <td style="font-size: 12px; color: var(--text-muted);">${item.required_by && item.required_by.length ? '被 ' + item.required_by.join(', ') + ' 依賴' : '無直接被依賴'}</td>
        `;
        tbody.appendChild(tr);
      });
      updateSelectedCount();
    }

    function toggleSelectPkg(name, checked) {
      if (checked) selectedPackages.add(name);
      else selectedPackages.delete(name);
      updateSelectedCount();
    }

    function toggleSelectAll(checked) {
      if (checked === undefined) {
        checked = selectedPackages.size === 0;
      }
      if (!currentData) return;
      if (checked) {
        currentData.orphans.tier3_pure_libraries.forEach(p => selectedPackages.add(p.name));
      } else {
        selectedPackages.clear();
      }
      renderPackageTable();
    }

    function updateSelectedCount() {
      document.getElementById('selectedCount').innerText = selectedPackages.size;
    }

    function renderNodeTable() {
      const tbody = document.getElementById('nodeTableBody');
      tbody.innerHTML = '';
      const nodeProjects = currentData.projects.filter(p => p.ecosystem === 'Node.js');
      if (nodeProjects.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color: var(--text-muted); padding: 20px;">未發現 Node.js 專案</td></tr>';
        return;
      }
      nodeProjects.forEach(p => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td style="font-weight: 600;">${p.name}</td>
          <td><span class="badge badge-active">Node.js</span></td>
          <td style="color: var(--text-muted);">${p.env_type}</td>
          <td style="font-size: 12px; color: var(--text-muted);">${p.path}</td>
          <td>${p.declared_deps.length} 個套件</td>
        `;
        tbody.appendChild(tr);
      });
    }

    function renderBloatTable() {
      const tbody = document.getElementById('bloatTableBody');
      tbody.innerHTML = '';
      if (!currentData || currentData.bloat.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color: var(--text-muted); padding: 20px;">未偵測到 Rust 或 Flutter 編譯贅肉</td></tr>';
        return;
      }
      currentData.bloat.forEach(b => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td style="font-weight: 600;">${b.project}</td>
          <td><span class="badge badge-tool">${b.ecosystem}</span></td>
          <td><code>${b.type}</code></td>
          <td style="color: var(--amber); font-weight: 700;">${b.size_mb} MB</td>
          <td style="font-size: 12px; color: var(--text-muted);">${b.path}</td>
          <td><button class="btn btn-danger" style="padding: 4px 10px; font-size: 11px;" onclick="cleanBloatItem('${b.path.replace(/\\/g, '\\\\')}')">清理</button></td>
        `;
        tbody.appendChild(tr);
      });
    }

    function confirmClean() {
      if (selectedPackages.size === 0) {
        alert('請先勾選欲卸載之套件！');
        return;
      }
      document.getElementById('modalDesc').innerText = `已選取 ${selectedPackages.size} 個套件。系統將在卸載前自動執行 pip freeze 快照存檔，若有誤刪可一鍵還原。`;
      document.getElementById('cleanModal').classList.add('active');
    }

    function closeModal() {
      document.getElementById('cleanModal').classList.remove('active');
    }

    async function executeClean() {
      closeModal();
      const pkgs = Array.from(selectedPackages);
      try {
        const res = await fetch('/api/clean-orphans', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({packages: pkgs})
        });
        const result = await res.json();
        if (result.success) {
          alert(`卸載成功！已清理 ${result.uninstalled.length} 個套件。\n備份保單已存至：${result.backup_file}`);
          selectedPackages.clear();
          startScan(); // Rescan
        } else {
          alert('卸載失敗: ' + (result.error || result.stderr));
        }
      } catch (e) {
        alert('請求錯誤: ' + e);
      }
    }

    async function cleanBloatItem(path) {
      if (!confirm(`確定要清理該目錄嗎？\n${path}`)) return;
      try {
        const res = await fetch('/api/clean-bloat', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({path: path})
        });
        const data = await res.json();
        if (data.success) {
          alert('清理成功！');
          startScan();
        } else {
          alert('清理失敗: ' + data.error);
        }
      } catch (e) {
        alert('清理錯誤: ' + e);
      }
    }

    async function loadBackups() {
      const tbody = document.getElementById('backupTableBody');
      tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">載入中...</td></tr>';
      try {
        const res = await fetch('/api/backups');
        const data = await res.json();
        tbody.innerHTML = '';
        if (data.backups.length === 0) {
          tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color: var(--text-muted); padding: 20px;">尚無任何備份檔案</td></tr>';
          return;
        }
        data.backups.forEach(b => {
          const tr = document.createElement('tr');
          const cmd = `pip install -r "${b.path}"`;
          tr.innerHTML = `
            <td style="font-weight: 600;">${b.name}</td>
            <td style="color: var(--text-muted);">${b.time}</td>
            <td>${(b.size / 1024).toFixed(1)} KB</td>
            <td>
              <code style="background:#0b0f19; padding: 4px 8px; border-radius: 4px; font-size: 11px;">${cmd}</code>
              <button class="btn" style="padding: 2px 8px; font-size: 11px; margin-left: 6px;" onclick="navigator.clipboard.writeText('${cmd.replace(/\\/g, '\\\\')}'); alert('已複製還原指令！');">複製</button>
            </td>
          `;
          tbody.appendChild(tr);
        });
      } catch (e) {
        tbody.innerHTML = `<tr><td colspan="4">載入失敗: ${e}</td></tr>`;
      }
    }

    // Auto-scan on load
    window.onload = () => {
      startScan();
    };
  </script>

  <footer style="margin-top: 40px; padding: 20px 0; border-top: 1px solid var(--card-border); display: flex; justify-content: space-between; align-items: center; font-size: 13px; color: var(--text-muted); flex-wrap: wrap; gap: 12px;">
    <div>
      <strong>orphan-clean</strong> v1.0.0 &bull; Released under the <a href="https://opensource.org/licenses/MIT" target="_blank" style="color: var(--cyan); text-decoration: none; font-weight: 600;">MIT License</a>.
    </div>
    <div style="display: flex; align-items: center; gap: 14px;">
      <span>喜歡這個工具嗎？</span>
      <a href="https://www.buymeacoffee.com/whoami885" target="_blank" style="display: inline-flex; align-items: center; gap: 6px; text-decoration: none; color: #000; background: #fbbf24; padding: 4px 12px; border-radius: 6px; font-weight: 700; font-size: 12px; box-shadow: 0 0 8px rgba(251, 191, 36, 0.2);" title="whoami885@gmail.com">
        <img src="https://cdn.buymeacoffee.com/buttons/bmc-new-btn-logo.svg" style="width: 14px; height: 14px;">
        Buy Me a Coffee
      </a>
    </div>
  </footer>
</body>
</html>
"""

class OrphanCleanHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global CURRENT_MATCHER
        if self.path in ["/", "/index.html"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
        elif self.path.startswith("/assets/"):
            # Serve asset file
            asset_name = self.path.split("/")[-1]
            asset_path = Path(__file__).parent.parent / "assets" / asset_name
            if asset_path.is_file():
                self.send_response(200)
                content_type = "image/png"
                if asset_name.endswith(".ico"):
                    content_type = "image/x-icon"
                self.send_header("Content-Type", content_type)
                self.end_headers()
                with open(asset_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Asset not found")
        elif self.path == "/api/backups":
            backups = []
            if CURRENT_MATCHER:
                backup_dir = CURRENT_MATCHER.root_dir / ".orphan_clean_backups"
                if backup_dir.is_dir():
                    for f in sorted(backup_dir.glob("pip_backup_*.txt"), reverse=True):
                        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                        backups.append({
                            "name": f.name,
                            "path": str(f),
                            "time": mtime,
                            "size": f.stat().st_size
                        })
            self._send_json({"backups": backups})
        else:
            self.send_error(404)

    def do_POST(self):
        global CURRENT_MATCHER
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        if self.path == "/api/scan":
            scan_path = payload.get("path", ".")
            CURRENT_MATCHER = LocalDependencyMatcher(scan_path)
            projects = CURRENT_MATCHER.scan()
            orphans = CURRENT_MATCHER.classify_orphans()
            bloat = CURRENT_MATCHER.scan_bloat()
            
            self._send_json({
                "projects": projects,
                "orphans": orphans,
                "bloat": bloat
            })
        elif self.path == "/api/clean-orphans":
            if not CURRENT_MATCHER:
                self._send_json({"success": False, "error": "No scan performed yet"})
                return
            packages = payload.get("packages", [])
            result = CURRENT_MATCHER.uninstall_packages(packages, backup=True)
            self._send_json(result)
        elif self.path == "/api/clean-bloat":
            if not CURRENT_MATCHER:
                self._send_json({"success": False, "error": "No scan performed yet"})
                return
            target_path = payload.get("path", "")
            result = CURRENT_MATCHER.clean_bloat_target(target_path)
            self._send_json(result)
        else:
            self.send_error(404)

    def _send_json(self, data: dict):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        # Suppress noisy HTTP request logging
        pass

def launch_app_window(url: str):
    """
    Open the Web UI in Chromium Application Mode (--app=...).
    This removes browser address bar, tabs, and buttons, giving it
    the appearance and feel of a native standalone desktop app window!
    """
    if sys.platform == "win32":
        candidates = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
        for exe in candidates:
            if os.path.isfile(exe):
                try:
                    subprocess.Popen([exe, f"--app={url}", "--window-size=1240,840"])
                    return
                except Exception:
                    pass
    elif sys.platform == "darwin":
        chrome_app = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.isfile(chrome_app):
            try:
                subprocess.Popen([chrome_app, f"--app={url}", "--window-size=1240,840"])
                return
            except Exception:
                pass
    webbrowser.open(url)

def run_server(port: int = 8765, open_browser: bool = True):
    global CURRENT_MATCHER
    server_address = ("127.0.0.1", port)
    
    # Port retry logic
    httpd = None
    for p in range(port, port + 10):
        try:
            httpd = HTTPServer(("127.0.0.1", p), OrphanCleanHandler)
            port = p
            break
        except OSError:
            continue

    if not httpd:
        print(f"[ERROR] Could not bind to any port in range {port}-{port+10}")
        return

    url = f"http://127.0.0.1:{port}"
    banner = r"""=================================================================
   ___             _                      ____ _                  
  / _ \ _ __ _ __ | |__   __ _ _ __      / ___| | ___  __ _ _ __  
 | | | | '__| '_ \| '_ \ / _` | '_ \ ___| |   | |/ _ \/ _` | '_ \ 
 | |_| | |  | |_) | | | | (_| | | | |___| |___| |  __/ (_| | | | |
  \___/|_|  | .__/|_| |_|\__,_|_| |_|    \____|_|\___|\__,_|_| |_|
            |_|                                                   
   [ Polyglot Dependency Auditor & Safe Orphan Cleaner v1.0 ]
================================================================="""
    print(banner)
    print(f"\n[*] orphan-clean Dashboard running at: {url}")
    print("[*] Press Ctrl+C or close the window to stop.\n")

    # Run HTTP server in background daemon thread
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    # Priority 1: Native Windows Desktop Window via pywebview (100% Native, NO Browser!)
    has_webview = False
    if open_browser:
        try:
            import webview
            has_webview = True
        except ImportError:
            has_webview = False

    if has_webview:
        try:
            window = webview.create_window(
                title="orphan-clean Dashboard",
                url=url,
                width=1240,
                height=840,
                min_size=(960, 600)
            )
            webview.start()
            print("\n[!] Native desktop window closed. Shutting down orphan-clean...")
            httpd.shutdown()
            return
        except Exception:
            pass

    # Priority 2: Fallback to Chromium --app mode or standard browser
    if open_browser:
        try:
            launch_app_window(url)
        except Exception:
            webbrowser.open(url)

    try:
        while server_thread.is_alive():
            server_thread.join(timeout=1.0)
    except KeyboardInterrupt:
        print("\n[!] Stopping orphan-clean Dashboard. Goodbye!")
        httpd.shutdown()

if __name__ == "__main__":
    run_server()
