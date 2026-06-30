let currentSubject = null;
const histories = {};
const pendingSubjects = new Set();

const elements = {
  subjectList: document.getElementById('subject-list'),
  newSubject: document.getElementById('new-subject'),
  fileInput: document.getElementById('file-input'),
  uploadStatus: document.getElementById('upload-status'),
  chatTitle: document.getElementById('chat-title'),
  chatStatus: document.getElementById('chat-status'),
  messages: document.getElementById('messages'),
  userInput: document.getElementById('user-input'),
  sendBtn: document.getElementById('send-btn'),
  addBtn: document.getElementById('add-btn'),
  uploadBtn: document.getElementById('upload-btn'),
  refreshBtn: document.getElementById('refresh-btn'),
};

function setStatus(text, isError = false) {
  elements.uploadStatus.textContent = text;
  elements.uploadStatus.style.color = isError ? '#b91c1c' : '#475569';
}

function updateChatState(enabled) {
  elements.userInput.disabled = !enabled;
  elements.sendBtn.disabled = !enabled;
  elements.userInput.placeholder = enabled ? '???? ????? ???' : '???? ???? ?????';
}

async function loadSubjects() {
  try {
    const response = await fetch('/materials');
    const data = await response.json();
    const serverSubjects = Array.isArray(data.subjects) ? data.subjects : [];
    serverSubjects.forEach((name) => pendingSubjects.delete(name));
    const subjects = [...new Set([...serverSubjects, ...pendingSubjects])].sort();
    renderSubjects(subjects);
  } catch {
    renderSubjects([...pendingSubjects].sort());
  }
}

function renderSubjects(subjects) {
  elements.subjectList.innerHTML = '';
  if (!subjects.length) {
    elements.subjectList.innerHTML = '<div class="empty-state">?? ???? ????</div>';
    return;
  }

  subjects.forEach((name) => {
    const item = document.createElement('div');
    item.className = `subject-item${name === currentSubject ? ' active' : ''}`;
    item.innerHTML = `
      <span>${name}</span>
      <button type="button" class="delete-btn" aria-label="??? ${name}">×</button>
    `;

    item.addEventListener('click', (event) => {
      if (event.target.closest('.delete-btn')) return;
      selectSubject(name);
    });

    const deleteBtn = item.querySelector('.delete-btn');
    deleteBtn.addEventListener('click', async (event) => {
      event.stopPropagation();
      await deleteSubject(name);
    });

    elements.subjectList.appendChild(item);
  });
}

function renderMessages() {
  const history = histories[currentSubject] || [];
  elements.messages.innerHTML = '';

  if (!history.length) {
    elements.messages.innerHTML = '<div class="empty-state">???? ???? ????? ?????. ???? ??????.</div>';
    return;
  }

  history.forEach((message) => {
    const msg = document.createElement('div');
    msg.className = `msg ${message.role === 'user' ? 'user' : 'ai'}`;
    msg.textContent = message.content;
    elements.messages.appendChild(msg);
  });
  elements.messages.scrollTop = elements.messages.scrollHeight;
}

function updateChatHeader() {
  elements.chatTitle.textContent = currentSubject || '???? ????';
  elements.chatStatus.textContent = currentSubject ? '' : '????? ??????? ?? ??????';
}

function selectSubject(subject) {
  currentSubject = subject;
  updateChatHeader();
  updateChatState(true);
  renderMessages();
  loadSubjects();
}

async function addSubject() {
  const value = elements.newSubject.value.trim();
  if (!value) return;
  elements.newSubject.value = '';
  pendingSubjects.add(value);
  histories[value] = histories[value] || [];
  selectSubject(value);
}

async function deleteSubject(subject) {
  if (!confirm(`??? "${subject}"?`)) return;
  pendingSubjects.delete(subject);
  try {
    await fetch(`/materials/${encodeURIComponent(subject)}`, { method: 'DELETE' });
  } catch {
    // ignore network error; remove locally anyway
  }
  if (currentSubject === subject) {
    currentSubject = null;
    updateChatHeader();
    updateChatState(false);
    elements.messages.innerHTML = '<div class="empty-state">???? ????</div>';
  }
  await loadSubjects();
}

async function uploadFile() {
  if (!currentSubject) {
    setStatus('???? ???? ?????', true);
    return;
  }

  if (!elements.fileInput.files.length) {
    setStatus('???? ?????', true);
    return;
  }

  const file = elements.fileInput.files[0];
  const formData = new FormData();
  formData.append('file', file);
  setStatus('???? ?????...');

  try {
    const response = await fetch(`/ingest/${encodeURIComponent(currentSubject)}`, {
      method: 'POST',
      body: formData,
    });
    const data = await response.json();
    if (response.ok) {
      setStatus(`?? ??? ?????. ${data.chunks || 0} chunks`);
      elements.fileInput.value = '';
      await loadSubjects();
    } else {
      setStatus(data.detail || '??? ?????', true);
    }
  } catch {
    setStatus('??? ???????', true);
  }
}

async function sendMessage() {
  const question = elements.userInput.value.trim();
  if (!question || !currentSubject) return;

  elements.userInput.value = '';
  elements.userInput.disabled = true;
  elements.sendBtn.disabled = true;

  histories[currentSubject] = histories[currentSubject] || [];
  histories[currentSubject].push({ role: 'user', content: question });
  renderMessages();

  const thinking = document.createElement('div');
  thinking.className = 'msg ai';
  thinking.textContent = '...';
  elements.messages.appendChild(thinking);
  elements.messages.scrollTop = elements.messages.scrollHeight;

  try {
    const response = await fetch(`/chat/${encodeURIComponent(currentSubject)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, history: histories[currentSubject].slice(-20) }),
    });
    const data = await response.json();
    histories[currentSubject].push({
      role: 'assistant',
      content: data.answer || data.detail || '??? ???',
    });
  } catch {
    histories[currentSubject].push({ role: 'assistant', content: '??? ???????' });
  }

  renderMessages();
  elements.userInput.disabled = false;
  elements.sendBtn.disabled = false;
  elements.userInput.focus();
}

function init() {
  elements.addBtn.addEventListener('click', addSubject);
  elements.uploadBtn.addEventListener('click', uploadFile);
  elements.sendBtn.addEventListener('click', sendMessage);
  elements.refreshBtn.addEventListener('click', loadSubjects);
  elements.userInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') sendMessage();
  });
  updateChatState(false);
  loadSubjects();
}

document.addEventListener('DOMContentLoaded', init);
