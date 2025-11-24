const TEMPLATES = {
    bug: {
        title: "Bug: ",
        body: `## Description
Brief description of the bug

## Steps to Reproduce
1. Step 1
2. Step 2
3. Step 3

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS:
- Browser:
- Version:

## Additional Context
Add any other context about the problem here.`
    },
    feature: {
        title: "Feature: ",
        body: `## Description
Brief description of the feature

## Problem Statement
What problem does this feature solve?

## Proposed Solution
How should this feature work?

## Alternatives Considered
Any alternative solutions or features considered

## Additional Context
Add any other context or screenshots about the feature request here.`
    },
    documentation: {
        title: "Docs: ",
        body: `## Documentation Update

### What needs to be documented?
Describe what documentation is missing or needs improvement

### Suggested Changes
Proposed documentation changes

### Related Files
List any related files or sections

### Additional Notes
Any additional information`
    },
    enhancement: {
        title: "Enhancement: ",
        body: `## Enhancement Description
Brief description of the enhancement

## Current Behavior
How does the current system work?

## Proposed Enhancement
How should it be improved?

## Benefits
What benefits will this enhancement bring?

## Implementation Notes
Any technical considerations`
    }
};

let currentStyles = {
    bold: false,
    italic: false,
    code: false
};

async function verifyCredentials() {
    const username = document.getElementById('username').value;
    const repoName = document.getElementById('repo-name').value;
    const token = document.getElementById('token').value;

    if (!username || !repoName || !token) {
        showResult('Please fill all authentication fields', 'error');
        return;
    }

    try {
        console.log('Sending verification request...');
        const apiUrl = `/api/verify-token?token=${encodeURIComponent(token)}&username=${encodeURIComponent(username)}&repo_name=${encodeURIComponent(repoName)}`;
        console.log('API URL:', apiUrl);

        const response = await fetch(apiUrl);
        console.log('Response status:', response.status);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Verification response:', data);

        if (data.valid && data.repo_exists) {
            document.getElementById('issue-section').style.display = 'block';
            showResult('✅ Credentials verified successfully!', 'success');
        } else {
            showResult('❌ Authentication failed: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Detailed error:', error);
        showResult('❌ Error: ' + error.message, 'error');
    }
}

function loadTemplate() {
    const templateSelect = document.getElementById('issue-template');
    const template = templateSelect.value;

    if (template && TEMPLATES[template]) {
        document.getElementById('issue-title').value = TEMPLATES[template].title;
        document.getElementById('issue-body').value = TEMPLATES[template].body;
        updatePreview();
    }
}

function applyStyle(style) {
    const textarea = document.getElementById('issue-body');
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selectedText = textarea.value.substring(start, end);

    let newText = '';

    switch(style) {
        case 'bold':
            newText = `**${selectedText}**`;
            break;
        case 'italic':
            newText = `*${selectedText}*`;
            break;
        case 'code':
            newText = `\`${selectedText}\``;
            break;
        case 'bullet':
            newText = selectedText.split('\n').map(line => `- ${line}`).join('\n');
            break;
        case 'number':
            newText = selectedText.split('\n').map((line, index) => `${index + 1}. ${line}`).join('\n');
            break;
        case 'quote':
            newText = selectedText.split('\n').map(line => `> ${line}`).join('\n');
            break;
    }

    textarea.value = textarea.value.substring(0, start) + newText + textarea.value.substring(end);
    updatePreview();
}

function updatePreview() {
    const markdown = document.getElementById('issue-body').value;
    // Simple markdown to HTML conversion for preview
    let html = markdown
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/> (.*)/g, '<blockquote>$1</blockquote>')
        .replace(/- (.*)/g, '<li>$1</li>')
        .replace(/(\d+)\. (.*)/g, '<li>$2</li>')
        .replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>')
        .replace(/\n/g, '<br>');

    document.getElementById('preview').innerHTML = html;
}

async function createIssue() {
    const username = document.getElementById('username').value;
    const repoName = document.getElementById('repo-name').value;
    const token = document.getElementById('token').value;
    const title = document.getElementById('issue-title').value;
    const body = document.getElementById('issue-body').value;

    if (!title || !body) {
        showResult('Please fill issue title and body', 'error');
        return;
    }

    try {
        const response = await fetch('/api/create-issue', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                title: title,
                body: body,
                token: token,
                username: username,
                repo_name: repoName
            })
        });

        const result = await response.json();

        if (result.success) {
            showResult(`Issue created successfully! <a href="${result.issue_url}" target="_blank">View Issue</a>`, 'success');
            // Clear form
            document.getElementById('issue-title').value = '';
            document.getElementById('issue-body').value = '';
            document.getElementById('preview').innerHTML = '';
        } else {
            showResult('Error creating issue: ' + result.message, 'error');
        }
    } catch (error) {
        showResult('Error creating issue: ' + error.message, 'error');
    }
}

function showResult(message, type) {
    const resultDiv = document.getElementById('result');
    resultDiv.innerHTML = message;
    resultDiv.className = `result ${type}`;
    resultDiv.style.display = 'block';
}

// Initialize event listeners
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('issue-body').addEventListener('input', updatePreview);
});