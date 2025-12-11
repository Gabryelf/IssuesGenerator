class GitHubIssuesCreator {
    constructor() {
        this.currentUser = null;
        this.currentRepository = null;
        this.currentTemplate = null;
        this.currentToken = null;
        this.templates = {};
        this.savedRepositories = [];

        this.baseUrl = '';
        this.apiEndpoints = {
            verify: '/api/verify',
            verifyToken: '/api/verify-token',
            templates: '/api/templates',
            templateDetails: '/api/templates/',
            createIssue: '/api/issues/create',
            createIssueCompat: '/api/create-issue', // For compatibility
            repositories: '/api/repositories',
            deleteRepository: '/api/repositories/',
            customTemplates: '/api/templates/custom',
            userTemplates: '/api/user/templates',
            health: '/health',
            test: '/api/test'
        };

        this.init();
    }

    async init() {
        console.log('🚀 GitHub Issues Creator Pro Initialized');
        console.log('📡 API Endpoints:', this.apiEndpoints);

        // Test API connection first
        await this.testApiConnection();

        // Load templates
        await this.loadTemplates();

        // Load saved repositories
        await this.loadSavedRepositories();

        // Set up event listeners
        this.setupEventListeners();

        // Check for URL parameters (for direct repository access)
        this.checkUrlParams();
    }

    async testApiConnection() {
        try {
            const response = await fetch(this.apiEndpoints.test);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data = await response.json();
            console.log('✅ API Connection Test:', data);
            this.logActivity('API connected successfully');
        } catch (error) {
            console.error('❌ API Connection Test failed:', error);
            this.showResult('API connection failed. Make sure server is running on port 8000.', 'error');
        }
    }

    async loadTemplates() {
        try {
            const response = await fetch(this.apiEndpoints.templates);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data = await response.json();

            if (data.success) {
                this.templates = data.templates;
                this.renderTemplates();
                console.log(`✅ Loaded ${data.templates.length} templates`);
            } else {
                this.showResult('Failed to load templates: ' + (data.message || 'Unknown error'), 'error');
            }
        } catch (error) {
            console.error('Error loading templates:', error);
            this.showResult('Error loading templates. Please check console (F12) for details.', 'error');
        }
    }

    async loadSavedRepositories() {
        try {
            const userId = this.getUserId();
            const response = await fetch(`${this.apiEndpoints.repositories}?user_id=${userId}`);

            if (!response.ok) {
                // If endpoint doesn't exist, just return empty array
                if (response.status === 404) {
                    console.log('⚠️  Repositories endpoint not found (Redis may be disabled)');
                    return;
                }
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                this.savedRepositories = data.repositories;
                this.renderSavedRepositories();
                console.log(`✅ Loaded ${data.repositories.length} saved repositories`);
            }
        } catch (error) {
            console.error('Error loading repositories:', error);
        }
    }

    setupEventListeners() {
        // Auto-refresh preview
        document.getElementById('issue-body').addEventListener('input', () => {
            this.updatePreview();
        });

        // Template selection
        document.getElementById('issue-title').addEventListener('input', () => {
            this.updatePreview();
        });

        // Enter key to submit in title field
        document.getElementById('issue-title').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                document.getElementById('issue-body').focus();
            }
        });

        // Auto-save draft every 30 seconds
        setInterval(() => {
            if (document.getElementById('issue-title').value || document.getElementById('issue-body').value) {
                this.saveAsDraft(true); // Silent save
            }
        }, 30000);
    }

    checkUrlParams() {
        const params = new URLSearchParams(window.location.search);
        const repo = params.get('repo');
        const template = params.get('template');

        if (repo) {
            document.getElementById('repo-name').value = repo;
        }

        if (template && this.templates[template]) {
            setTimeout(() => this.selectTemplate(template), 1000);
        }
    }

    getUserId() {
        let userId = localStorage.getItem('github_issues_user_id');
        if (!userId) {
            userId = 'user_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('github_issues_user_id', userId);
        }
        return userId;
    }

    renderTemplates() {
        const templateGrid = document.getElementById('template-grid');
        if (!templateGrid) {
            console.error('Template grid element not found');
            return;
        }

        templateGrid.innerHTML = '';

        const templateIcons = {
            'bug_report': 'fas fa-bug',
            'feature_request': 'fas fa-star',
            'documentation': 'fas fa-book',
            'security': 'fas fa-shield-alt',
            'code_review': 'fas fa-code-branch'
        };

        Object.values(this.templates).forEach(template => {
            const card = document.createElement('div');
            card.className = 'template-card';
            card.dataset.templateName = template.name;

            card.innerHTML = `
                <div class="template-icon">
                    <i class="${templateIcons[template.name] || 'fas fa-file-alt'}"></i>
                </div>
                <h4 class="template-title">${template.title || template.name}</h4>
                <p class="template-description">${template.description || 'No description'}</p>
                <div class="template-tags">
                    ${template.labels ? template.labels.map(label =>
                        `<span class="tag">${label}</span>`
                    ).join('') : ''}
                </div>
                <button class="btn btn-sm btn-primary" onclick="selectTemplate('${template.name}')">
                    Use Template
                </button>
            `;

            templateGrid.appendChild(card);
        });
    }

    renderSavedRepositories() {
        const reposContainer = document.getElementById('saved-repos');
        if (!reposContainer) {
            console.error('Saved repos container not found');
            return;
        }

        if (this.savedRepositories.length === 0) {
            reposContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-box-open"></i>
                    <p>No saved repositories yet</p>
                    <small>Connect to a repository and check "Save connection"</small>
                </div>
            `;
            return;
        }

        reposContainer.innerHTML = '';

        this.savedRepositories.forEach(repo => {
            const card = document.createElement('div');
            card.className = 'repo-card';

            card.innerHTML = `
                <div class="repo-card-header">
                    <h4 class="repo-name">${repo.repo_name}</h4>
                    <button class="repo-delete-btn" onclick="deleteRepository('${repo.repo_name}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
                <div class="repo-info">
                    <span class="repo-owner">
                        <i class="fas fa-user"></i> ${repo.username}
                    </span>
                    ${repo.metadata?.verified_at ?
                        `<span class="repo-date">
                            <i class="fas fa-calendar"></i> ${new Date(repo.metadata.verified_at).toLocaleDateString()}
                        </span>` : ''}
                </div>
                <div class="repo-actions">
                    <button class="btn btn-sm btn-outline" onclick="useRepository('${repo.repo_name}', '${repo.username}')">
                        <i class="fas fa-edit"></i> Use
                    </button>
                </div>
            `;

            reposContainer.appendChild(card);
        });
    }

    async verifyAndConnect() {
        const username = document.getElementById('username').value.trim();
        const repoName = document.getElementById('repo-name').value.trim();
        const token = document.getElementById('token').value.trim();
        const saveToRedis = document.getElementById('save-to-redis').checked;

        if (!username || !repoName || !token) {
            this.showResult('Please fill all required fields', 'error');
            return;
        }

        // Basic token validation
        if (!token.startsWith('ghp_') && !token.startsWith('github_pat_')) {
            if (!confirm('This doesn\'t look like a valid GitHub token. Continue anyway?')) {
                return;
            }
        }

        this.showLoading('Verifying credentials...');

        try {
            const connectionData = {
                username: username,
                repo_name: repoName,
                token: token,
                save_to_redis: saveToRedis,
                metadata: {
                    user_agent: navigator.userAgent,
                    timestamp: new Date().toISOString()
                }
            };

            console.log('📤 POST to:', this.apiEndpoints.verify);
            console.log('📦 Data:', { ...connectionData, token: '***' });

            const response = await fetch(this.apiEndpoints.verify, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(connectionData)
            });

            console.log('📥 Response status:', response.status);

            let result;
            try {
                result = await response.json();
            } catch (e) {
                console.error('Failed to parse JSON response:', e);
                throw new Error(`Server returned invalid JSON (${response.status})`);
            }

            console.log('📥 Response data:', result);

            if (result.success) {
                this.currentUser = username;
                this.currentRepository = repoName;
                this.currentToken = token;

                this.showResult('✅ Successfully connected to repository!', 'success');

                // Show template section
                document.getElementById('connection-section').classList.add('hidden');
                document.getElementById('template-section').classList.remove('hidden');

                // Log activity
                this.logActivity(`Connected to ${username}/${repoName}`);

                // Reload saved repositories if saved
                if (saveToRedis) {
                    setTimeout(() => this.loadSavedRepositories(), 1000);
                }

                // Show repository info if available
                if (result.data && result.data.repo_data) {
                    const repo = result.data.repo_data;
                    console.log('📊 Repository info:', repo);
                    this.logActivity(`Repository: ${repo.full_name} (${repo.private ? 'Private' : 'Public'})`);
                }

                // Auto-load draft if exists
                setTimeout(() => this.loadDraft(), 500);
            } else {
                this.showResult('❌ ' + (result.message || 'Connection failed'), 'error');
            }
        } catch (error) {
            console.error('Verification error:', error);
            this.showResult('❌ Connection error: ' + error.message, 'error');
        }
    }

    async selectTemplate(templateName) {
        try {
            const response = await fetch(`${this.apiEndpoints.templateDetails}${templateName}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                this.currentTemplate = data.data.template;

                // Populate form with template
                document.getElementById('issue-title').value = this.currentTemplate.title;
                document.getElementById('issue-body').value = this.currentTemplate.body;

                // Render template fields
                this.renderTemplateFields(data.data.fields);

                // Show issue creation section
                document.getElementById('template-section').classList.add('hidden');
                document.getElementById('issue-creation-section').classList.remove('hidden');

                // Show template preview
                this.showTemplatePreview();

                // Update preview immediately
                this.updatePreview();

                this.showResult(`✅ Template "${templateName}" loaded`, 'success');
                this.logActivity(`Selected template: ${templateName}`);
            }
        } catch (error) {
            console.error('Error loading template:', error);
            this.showResult('Error loading template: ' + error.message, 'error');
        }
    }

    renderTemplateFields(fields) {
        const container = document.getElementById('template-fields');
        if (!container) return;

        container.innerHTML = '';

        if (!fields || fields.length === 0) {
            container.classList.add('hidden');
            return;
        }

        container.classList.remove('hidden');

        fields.forEach(field => {
            const fieldGroup = document.createElement('div');
            fieldGroup.className = 'field-group';

            let fieldHtml = `
                <label for="field-${field.name}">
                    ${field.label}
                    ${field.required ? ' <span style="color: #ff6b6b;">*</span>' : ''}
                </label>
            `;

            switch (field.type) {
                case 'textarea':
                    fieldHtml += `
                        <textarea
                            id="field-${field.name}"
                            class="form-textarea"
                            rows="4"
                            placeholder="${field.placeholder || ''}"
                            ${field.required ? 'required' : ''}
                            oninput="app.updatePreview()"
                        >${field.default_value || ''}</textarea>
                    `;
                    break;

                case 'select':
                    fieldHtml += `
                        <select
                            id="field-${field.name}"
                            class="form-input"
                            ${field.required ? 'required' : ''}
                            onchange="app.updatePreview()"
                        >
                            <option value="">${field.placeholder || 'Select an option'}</option>
                            ${field.options ? field.options.map(opt =>
                                `<option value="${opt}" ${field.default_value === opt ? 'selected' : ''}>${opt}</option>`
                            ).join('') : ''}
                        </select>
                    `;
                    break;

                case 'checkbox':
                    fieldHtml += `
                        <div class="checkbox">
                            <input
                                type="checkbox"
                                id="field-${field.name}"
                                ${field.default_value ? 'checked' : ''}
                                onchange="app.updatePreview()"
                            >
                            <span class="checkmark"></span>
                            <span>${field.label}</span>
                        </div>
                    `;
                    break;

                default: // text
                    fieldHtml += `
                        <input
                            type="text"
                            id="field-${field.name}"
                            class="form-input"
                            placeholder="${field.placeholder || ''}"
                            value="${field.default_value || ''}"
                            ${field.required ? 'required' : ''}
                            oninput="app.updatePreview()"
                        >
                    `;
            }

            fieldGroup.innerHTML = fieldHtml;
            container.appendChild(fieldGroup);
        });
    }

    showTemplatePreview() {
        const previewContainer = document.getElementById('template-preview');
        const previewContent = document.getElementById('template-preview-content');

        if (!previewContainer || !previewContent) return;

        if (this.currentTemplate) {
            const shortBody = this.currentTemplate.body.length > 500
                ? this.currentTemplate.body.substring(0, 500) + '...'
                : this.currentTemplate.body;

            previewContent.innerHTML = `
                <h4 style="margin-bottom: 10px;">${this.currentTemplate.title}</h4>
                <p style="color: #8b949e; margin-bottom: 15px;"><small>${this.currentTemplate.description}</small></p>
                <div style="background: #161b22; padding: 15px; border-radius: 6px; font-size: 0.85em; max-height: 200px; overflow-y: auto;">
                    <pre style="margin: 0; white-space: pre-wrap; color: #c9d1d9;">${shortBody}</pre>
                </div>
            `;
            previewContainer.classList.remove('hidden');
        }
    }

    async createIssue() {
        if (!this.currentUser || !this.currentRepository || !this.currentToken) {
            this.showResult('Please connect to a repository first', 'error');
            return;
        }

        const title = document.getElementById('issue-title').value.trim();
        const body = document.getElementById('issue-body').value.trim();

        if (!title) {
            this.showResult('Please enter issue title', 'error');
            document.getElementById('issue-title').focus();
            return;
        }

        if (!body) {
            this.showResult('Please enter issue body', 'error');
            document.getElementById('issue-body').focus();
            return;
        }

        // Check required fields
        const requiredFields = document.querySelectorAll('[id^="field-"][required]');
        for (const field of requiredFields) {
            if (!field.value.trim()) {
                this.showResult(`Please fill required field: ${field.id.replace('field-', '')}`, 'error');
                field.focus();
                return;
            }
        }

        this.showLoading('Creating issue...');

        try {
            // Get template field values
            const fieldValues = {};
            const fields = document.querySelectorAll('[id^="field-"]');
            fields.forEach(field => {
                const fieldName = field.id.replace('field-', '');
                if (field.type === 'checkbox') {
                    fieldValues[fieldName] = field.checked;
                } else {
                    fieldValues[fieldName] = field.value;
                }
            });

            // Replace placeholders in body
            let finalBody = body;
            Object.entries(fieldValues).forEach(([key, value]) => {
                const placeholder = new RegExp(`\\{${key}\\}`, 'g');
                finalBody = finalBody.replace(placeholder, value);
            });

            const issueData = {
                title: title,
                body: finalBody,
                token: this.currentToken,
                username: this.currentUser,
                repo_name: this.currentRepository,
                labels: this.currentTemplate ? this.currentTemplate.labels : []
            };

            console.log('📤 Creating issue with data:', {
                ...issueData,
                token: '***',
                body_preview: finalBody.substring(0, 100) + '...'
            });

            // Try main endpoint first, then compatibility endpoint
            let response;
            try {
                console.log('Trying main endpoint:', this.apiEndpoints.createIssue);
                response = await fetch(this.apiEndpoints.createIssue, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(issueData)
                });
            } catch (mainError) {
                console.log('Main endpoint failed, trying compatibility:', mainError);
                response = await fetch(this.apiEndpoints.createIssueCompat, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(issueData)
                });
            }

            console.log('📥 Response status:', response.status);

            let result;
            try {
                result = await response.json();
            } catch (e) {
                console.error('Failed to parse JSON response:', e);
                const text = await response.text();
                console.error('Raw response:', text);
                throw new Error(`Server returned invalid JSON (${response.status}): ${text.substring(0, 100)}`);
            }

            console.log('📥 Response data:', result);

            if (result.success) {
                const issueNumber = result.data?.issue_number || 'N/A';
                const issueUrl = result.issue_url || '#';

                this.showResult(`
                    <div style="text-align: center;">
                        <div style="font-size: 24px; margin-bottom: 10px;">✅</div>
                        <h3 style="margin-bottom: 10px;">Issue Created Successfully!</h3>
                        <p style="margin-bottom: 20px;">Issue #${issueNumber} has been created in ${this.currentUser}/${this.currentRepository}</p>
                        <a href="${issueUrl}" target="_blank"
                           style="display: inline-block; background: #238636; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: bold;">
                            <i class="fas fa-external-link-alt"></i> View Issue #${issueNumber}
                        </a>
                    </div>
                `, 'success');

                // Log activity
                this.logActivity(`Created issue: ${title} (#${issueNumber})`);

                // Clear draft
                localStorage.removeItem('issue_draft');

                // Clear form after 5 seconds
                setTimeout(() => {
                    this.clearForm();
                    this.showResult('Form cleared. Ready to create another issue.', 'info');
                }, 5000);
            } else {
                this.showResult('❌ ' + (result.message || 'Failed to create issue'), 'error');
            }
        } catch (error) {
            console.error('Error creating issue:', error);
            this.showResult('❌ Error creating issue: ' + error.message, 'error');
        }
    }

    async useRepository(repoName, username) {
        const userId = this.getUserId();

        try {
            const response = await fetch(`${this.apiEndpoints.repositories}?user_id=${userId}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                const repo = data.repositories.find(r => r.repo_name === repoName && r.username === username);
                if (repo) {
                    document.getElementById('username').value = username;
                    document.getElementById('repo-name').value = repoName;

                    this.showResult(`✅ Repository ${repoName} loaded. Enter your token to continue.`, 'success');
                    document.getElementById('token').focus();

                    this.logActivity(`Loaded repository: ${username}/${repoName}`);
                }
            }
        } catch (error) {
            console.error('Error loading repository:', error);
            this.showResult('Error loading repository. Please enter details manually.', 'error');
        }
    }

    async deleteRepository(repoName) {
        if (!confirm(`Are you sure you want to remove "${repoName}" from saved repositories?`)) {
            return;
        }

        const userId = this.getUserId();

        try {
            const response = await fetch(`${this.apiEndpoints.deleteRepository}${repoName}?user_id=${userId}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.success) {
                this.showResult(`✅ Repository "${repoName}" removed`, 'success');
                await this.loadSavedRepositories();
                this.logActivity(`Deleted repository: ${repoName}`);
            } else {
                this.showResult('Error removing repository: ' + (result.message || 'Unknown error'), 'error');
            }
        } catch (error) {
            console.error('Error deleting repository:', error);
            this.showResult('Error removing repository: ' + error.message, 'error');
        }
    }

    logActivity(message) {
        const activityLog = document.getElementById('activity-log');
        if (!activityLog) return;

        const now = new Date();
        const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        const activityItem = document.createElement('div');
        activityItem.className = 'activity-item';
        activityItem.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div style="flex: 1;">
                    <div style="font-weight: 500; margin-bottom: 2px;">${message}</div>
                    <small style="color: #8b949e;">${timeString}</small>
                </div>
                <div style="color: #8b949e; font-size: 12px;">
                    <i class="fas fa-circle" style="font-size: 6px;"></i>
                </div>
            </div>
        `;

        activityLog.insertBefore(activityItem, activityLog.firstChild);

        // Keep only last 10 activities
        while (activityLog.children.length > 10) {
            activityLog.removeChild(activityLog.lastChild);
        }
    }

    updatePreview() {
        const markdown = document.getElementById('issue-body').value;
        const preview = document.getElementById('preview');

        if (!preview) return;

        if (!markdown.trim()) {
            preview.innerHTML = '<p style="color: #8b949e; text-align: center; padding: 40px;">Preview will appear here</p>';
            return;
        }

        // Get field values for placeholder replacement
        const fieldValues = {};
        const fields = document.querySelectorAll('[id^="field-"]');
        fields.forEach(field => {
            const fieldName = field.id.replace('field-', '');
            if (field.type === 'checkbox') {
                fieldValues[fieldName] = field.checked ? '✓ Yes' : '✗ No';
            } else {
                fieldValues[fieldName] = field.value;
            }
        });

        // Replace placeholders
        let processedMarkdown = markdown;
        Object.entries(fieldValues).forEach(([key, value]) => {
            const placeholder = new RegExp(`\\{${key}\\}`, 'g');
            processedMarkdown = processedMarkdown.replace(placeholder, value);
        });

        // Simple markdown to HTML conversion
        let html = processedMarkdown
            // Headers
            .replace(/^# (.*$)/gm, '<h1>$1</h1>')
            .replace(/^## (.*$)/gm, '<h2>$1</h2>')
            .replace(/^### (.*$)/gm, '<h3>$1</h3>')
            .replace(/^#### (.*$)/gm, '<h4>$1</h4>')
            .replace(/^##### (.*$)/gm, '<h5>$1</h5>')
            .replace(/^###### (.*$)/gm, '<h6>$1</h6>')
            // Bold and italic
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // Code
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            // Code blocks with language
            .replace(/```(\w+)?\n([\s\S]*?)\n```/g, '<pre><code class="language-$1">$2</code></pre>')
            // Links
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
            // Images
            .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1" style="max-width: 100%; border-radius: 6px; margin: 10px 0;">')
            // Lists
            .replace(/^- (.*)/gm, '<li>$1</li>')
            .replace(/^(\d+)\. (.*)/gm, '<li>$2</li>')
            // Blockquotes
            .replace(/^> (.*)/gm, '<blockquote>$1</blockquote>')
            // Horizontal rule
            .replace(/^---$/gm, '<hr>')
            // Line breaks and paragraphs
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');

        // Wrap list items
        html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');

        // Add paragraphs
        html = `<p>${html}</p>`;

        // Clean up empty paragraphs
        html = html.replace(/<p>\s*<\/p>/g, '');

        preview.innerHTML = html;
    }

    refreshPreview() {
        this.updatePreview();
        this.showResult('Preview refreshed', 'info');
    }

    clearForm() {
        document.getElementById('issue-title').value = '';
        document.getElementById('issue-body').value = '';

        const fieldsContainer = document.getElementById('template-fields');
        if (fieldsContainer) {
            fieldsContainer.innerHTML = '';
            fieldsContainer.classList.add('hidden');
        }

        const preview = document.getElementById('preview');
        if (preview) {
            preview.innerHTML = '<p style="color: #8b949e; text-align: center; padding: 40px;">Preview will appear here</p>';
        }

        this.currentTemplate = null;

        // Show template selection again
        document.getElementById('issue-creation-section').classList.add('hidden');
        document.getElementById('template-section').classList.remove('hidden');

        this.logActivity('Form cleared');
    }

    saveAsDraft(silent = false) {
        const title = document.getElementById('issue-title').value;
        const body = document.getElementById('issue-body').value;

        if (!title && !body) return;

        const issueData = {
            title: title,
            body: body,
            template: this.currentTemplate?.name,
            timestamp: new Date().toISOString(),
            repository: this.currentRepository ? `${this.currentUser}/${this.currentRepository}` : null
        };

        localStorage.setItem('issue_draft', JSON.stringify(issueData));

        if (!silent) {
            this.showResult('Draft saved locally', 'info');
            this.logActivity('Draft saved');
        }
    }

    loadDraft() {
        const draft = localStorage.getItem('issue_draft');
        if (draft) {
            try {
                const issueData = JSON.parse(draft);

                // Only load if we're in the issue creation section
                const issueSection = document.getElementById('issue-creation-section');
                if (issueSection && !issueSection.classList.contains('hidden')) {
                    document.getElementById('issue-title').value = issueData.title || '';
                    document.getElementById('issue-body').value = issueData.body || '';
                    this.updatePreview();

                    if (issueData.title || issueData.body) {
                        this.showResult('Draft loaded from local storage', 'info');
                        this.logActivity('Loaded draft');
                    }
                }
            } catch (e) {
                console.error('Error loading draft:', e);
            }
        }
    }

    showResult(message, type = 'info') {
        const resultDiv = document.getElementById('result');
        if (!resultDiv) return;

        const typeClasses = {
            success: 'success',
            error: 'error',
            warning: 'warning',
            info: 'info'
        };

        resultDiv.innerHTML = message;
        resultDiv.className = `result ${typeClasses[type] || 'info'}`;
        resultDiv.classList.remove('hidden');

        // Auto-hide success/info messages after 5 seconds
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                if (resultDiv.innerHTML === message) {
                    resultDiv.classList.add('hidden');
                }
            }, 5000);
        }
    }

    showLoading(message) {
        const resultDiv = document.getElementById('result');
        if (!resultDiv) return;

        resultDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 12px;">
                <div class="spinner"></div>
                <span>${message}</span>
            </div>
        `;
        resultDiv.className = 'result';
        resultDiv.classList.remove('hidden');
    }

    applyStyle(style) {
        const textarea = document.getElementById('issue-body');
        if (!textarea) return;

        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const selectedText = textarea.value.substring(start, end);

        let newText = '';
        let cursorOffset = 0;

        switch(style) {
            case 'bold':
                newText = `**${selectedText}**`;
                cursorOffset = selectedText ? 0 : 2;
                break;
            case 'italic':
                newText = `*${selectedText}*`;
                cursorOffset = selectedText ? 0 : 1;
                break;
            case 'code':
                newText = selectedText.includes('\n') ?
                    `\`\`\`\n${selectedText}\n\`\`\`` :
                    `\`${selectedText}\``;
                cursorOffset = selectedText ? 0 : (selectedText.includes('\n') ? 4 : 1);
                break;
            case 'bullet':
                newText = selectedText.split('\n').map(line => line.trim() ? `- ${line}` : '').join('\n');
                break;
            case 'number':
                newText = selectedText.split('\n')
                    .map((line, index) => line.trim() ? `${index + 1}. ${line}` : '')
                    .join('\n');
                break;
            case 'quote':
                newText = selectedText.split('\n').map(line => `> ${line}`).join('\n');
                break;
            case 'link':
                newText = `[${selectedText || 'link text'}](${selectedText ? 'url' : 'https://example.com'})`;
                cursorOffset = selectedText ? 3 : 1;
                break;
            case 'image':
                newText = `![${selectedText || 'alt text'}](${selectedText ? 'image-url' : 'https://example.com/image.jpg'})`;
                cursorOffset = selectedText ? 4 : 2;
                break;
            default:
                return;
        }

        textarea.value = textarea.value.substring(0, start) +
                        newText +
                        textarea.value.substring(end);

        // Set cursor position
        const newCursorPos = start + newText.length - cursorOffset;
        textarea.setSelectionRange(newCursorPos, newCursorPos);
        textarea.focus();

        this.updatePreview();
    }

    toggleTokenVisibility() {
        const tokenInput = document.getElementById('token');
        if (!tokenInput) return;

        const eyeIcon = tokenInput.parentNode.querySelector('i');
        if (!eyeIcon) return;

        if (tokenInput.type === 'password') {
            tokenInput.type = 'text';
            eyeIcon.className = 'fas fa-eye-slash';
            eyeIcon.title = 'Hide token';
        } else {
            tokenInput.type = 'password';
            eyeIcon.className = 'fas fa-eye';
            eyeIcon.title = 'Show token';
        }
    }
}

// Initialize the application
let app;

document.addEventListener('DOMContentLoaded', () => {
    app = new GitHubIssuesCreator();

    // Add spinner CSS
    const style = document.createElement('style');
    style.textContent = `
        .spinner {
            border: 2px solid rgba(35, 134, 54, 0.3);
            border-radius: 50%;
            border-top: 2px solid var(--primary-color, #238636);
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .result.info {
            background: rgba(13, 110, 253, 0.1);
            border: 1px solid #0d6efd;
            color: #0d6efd;
        }

        .result.warning {
            background: rgba(255, 193, 7, 0.1);
            border: 1px solid #ffc107;
            color: #ffc107;
        }
    `;
    document.head.appendChild(style);

    // Add global debug info
    console.log('🌐 GitHub Issues Creator Pro initialized');
    console.log('📍 Current URL:', window.location.href);
    console.log('🕒 Time:', new Date().toLocaleString());
});

// Global functions for HTML onclick attributes
function verifyAndConnect() {
    if (app && app.verifyAndConnect) {
        app.verifyAndConnect();
    } else {
        console.error('App not initialized or verifyAndConnect not found');
        alert('Application not initialized. Please refresh the page.');
    }
}

function selectTemplate(name) {
    if (app && app.selectTemplate) {
        app.selectTemplate(name);
    } else {
        console.error('App not initialized or selectTemplate not found');
    }
}

function createIssue() {
    if (app && app.createIssue) {
        app.createIssue();
    } else {
        console.error('App not initialized or createIssue not found');
        alert('Please connect to a repository first.');
    }
}

function applyStyle(style) {
    if (app && app.applyStyle) {
        app.applyStyle(style);
    } else {
        console.error('App not initialized or applyStyle not found');
    }
}

function refreshPreview() {
    if (app && app.refreshPreview) {
        app.refreshPreview();
    } else {
        console.error('App not initialized or refreshPreview not found');
    }
}

function clearForm() {
    if (app && app.clearForm) {
        if (confirm('Are you sure you want to clear the form?')) {
            app.clearForm();
        }
    } else {
        console.error('App not initialized or clearForm not found');
    }
}

function saveAsDraft() {
    if (app && app.saveAsDraft) {
        app.saveAsDraft();
    } else {
        console.error('App not initialized or saveAsDraft not found');
    }
}

function useRepository(repoName, username) {
    if (app && app.useRepository) {
        app.useRepository(repoName, username);
    } else {
        console.error('App not initialized or useRepository not found');
    }
}

function deleteRepository(repoName) {
    if (app && app.deleteRepository) {
        app.deleteRepository(repoName);
    } else {
        console.error('App not initialized or deleteRepository not found');
    }
}

function toggleTokenVisibility() {
    if (app && app.toggleTokenVisibility) {
        app.toggleTokenVisibility();
    } else {
        console.error('App not initialized or toggleTokenVisibility not found');
    }
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl+Enter to create issue (when in issue creation)
    if (e.ctrlKey && e.key === 'Enter') {
        const issueSection = document.getElementById('issue-creation-section');
        if (issueSection && !issueSection.classList.contains('hidden')) {
            e.preventDefault();
            createIssue();
        }
    }

    // Ctrl+S to save draft
    if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        saveAsDraft();
    }

    // Ctrl+D for debug
    if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        e.preventDefault();
        console.log('=== DEBUG INFO ===');
        console.log('App:', app);
        console.log('Current User:', app?.currentUser);
        console.log('Current Repo:', app?.currentRepository);
        console.log('Current Template:', app?.currentTemplate);
        console.log('Local Storage Draft:', localStorage.getItem('issue_draft'));
        console.log('==================');
        alert('Debug info logged to console (F12)');
    }
});