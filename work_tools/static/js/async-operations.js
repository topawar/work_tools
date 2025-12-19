/**
 * 异步操作处理器
 * 提供文件上传、表单提交等异步操作的进度反馈
 */

class AsyncOperationManager {
    constructor() {
        this.operations = new Map();
        this.init();
    }

    init() {
        this.setupFormInterceptors();
        this.setupFileUploadHandlers();
    }

    /**
     * 拦截表单提交，添加异步处理
     */
    setupFormInterceptors() {
        document.addEventListener('submit', (e) => {
            const form = e.target;
            
            // 检查是否有文件上传
            const hasFileInput = form.querySelector('input[type="file"]');
            const fileInput = hasFileInput && hasFileInput.files.length > 0;
            
            // 如果有文件上传或表单较复杂，使用异步处理
            if (fileInput || form.elements.length > 5) {
                e.preventDefault();
                this.handleAsyncSubmit(form);
            }
        });
    }

    /**
     * 处理异步表单提交
     */
    async handleAsyncSubmit(form) {
        const operationId = this.generateOperationId();
        const formData = new FormData(form);
        
        // 显示进度
        const progress = this.createProgressIndicator(form);
        progress.show();
        
        try {
            // 模拟进度更新
            this.simulateProgress(progress, operationId);
            
            // 提交表单
            const response = await fetch(form.action || window.location.href, {
                method: form.method || 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            // 完成进度
            progress.setProgress(100);
            
            if (response.ok) {
                const contentType = response.headers.get('content-type');
                
                if (contentType && contentType.includes('application/json')) {
                    // JSON响应
                    const data = await response.json();
                    this.handleJsonResponse(data, form);
                } else {
                    // HTML响应 - 重定向或更新页面
                    const html = await response.text();
                    this.handleHtmlResponse(html, response.url);
                }
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
        } catch (error) {
            console.error('Form submission error:', error);
            window.ui.showToast('提交失败: ' + error.message, 'error');
        } finally {
            progress.hide();
            this.operations.delete(operationId);
        }
    }

    /**
     * 处理JSON响应
     */
    handleJsonResponse(data, form) {
        if (data.success) {
            window.ui.showToast(data.message || '操作成功', 'success');
            
            if (data.redirect) {
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 1000);
            } else if (data.reload) {
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            }
        } else {
            window.ui.showToast(data.message || '操作失败', 'error');
            
            // 显示字段错误
            if (data.errors) {
                this.displayFormErrors(form, data.errors);
            }
        }
    }

    /**
     * 处理HTML响应
     */
    handleHtmlResponse(html, url) {
        // 如果URL发生变化，说明是重定向
        if (url !== window.location.href) {
            window.location.href = url;
        } else {
            // 更新页面内容
            document.documentElement.innerHTML = html;
            
            // 重新初始化UI增强
            if (window.ui) {
                window.ui.onReady();
            }
        }
    }

    /**
     * 显示表单错误
     */
    displayFormErrors(form, errors) {
        // 清除之前的错误
        form.querySelectorAll('.form-error').forEach(el => el.remove());
        form.querySelectorAll('.error').forEach(el => el.classList.remove('error'));
        
        // 显示新错误
        Object.keys(errors).forEach(fieldName => {
            const field = form.querySelector(`[name="${fieldName}"]`);
            if (field) {
                field.classList.add('error');
                
                const errorDiv = document.createElement('div');
                errorDiv.className = 'form-error';
                errorDiv.textContent = errors[fieldName].join(', ');
                
                field.parentNode.appendChild(errorDiv);
            }
        });
    }

    /**
     * 设置文件上传处理器
     */
    setupFileUploadHandlers() {
        document.addEventListener('change', (e) => {
            if (e.target.type === 'file') {
                this.handleFileSelection(e.target);
            }
        });
    }

    /**
     * 处理文件选择
     */
    handleFileSelection(input) {
        const files = Array.from(input.files);
        
        if (files.length === 0) return;
        
        // 验证文件
        const validationResult = this.validateFiles(files);
        
        if (!validationResult.valid) {
            window.ui.showToast(validationResult.message, 'error');
            input.value = ''; // 清除无效文件
            return;
        }
        
        // 显示文件信息
        this.displayFileInfo(input, files);
    }

    /**
     * 验证文件
     */
    validateFiles(files) {
        const maxSize = 10 * 1024 * 1024; // 10MB
        const allowedTypes = [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
            'application/vnd.ms-excel', // .xls
            'text/csv'
        ];
        
        for (const file of files) {
            if (file.size > maxSize) {
                return {
                    valid: false,
                    message: `文件 "${file.name}" 超过最大大小限制 (10MB)`
                };
            }
            
            if (!allowedTypes.includes(file.type)) {
                return {
                    valid: false,
                    message: `文件 "${file.name}" 类型不支持，请选择Excel或CSV文件`
                };
            }
        }
        
        return { valid: true };
    }

    /**
     * 显示文件信息
     */
    displayFileInfo(input, files) {
        const wrapper = input.closest('.file-upload');
        if (!wrapper) return;
        
        let infoDiv = wrapper.querySelector('.file-info');
        if (!infoDiv) {
            infoDiv = document.createElement('div');
            infoDiv.className = 'file-info';
            infoDiv.style.cssText = `
                margin-top: 8px;
                padding: 8px 12px;
                background: #f0f4ff;
                border: 1px solid #c7d2fe;
                border-radius: 6px;
                font-size: 13px;
                color: #3730a3;
            `;
            wrapper.appendChild(infoDiv);
        }
        
        const file = files[0];
        const sizeText = this.formatFileSize(file.size);
        
        infoDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <i class="bi bi-file-earmark-check" style="color: #059669;"></i>
                <div>
                    <div style="font-weight: 500;">${file.name}</div>
                    <div style="font-size: 12px; opacity: 0.8;">大小: ${sizeText}</div>
                </div>
            </div>
        `;
    }

    /**
     * 格式化文件大小
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * 创建进度指示器
     */
    createProgressIndicator(form) {
        const container = document.createElement('div');
        container.className = 'operation-progress';
        container.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
            min-width: 300px;
            z-index: 10000;
            transform: translateY(100%);
            transition: transform 0.3s ease;
        `;
        
        container.innerHTML = `
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
                <div class="loading-spinner" style="width: 20px; height: 20px;"></div>
                <div style="font-weight: 500; color: #374151;">正在处理...</div>
            </div>
            <div class="progress-bar">
                <div class="progress-fill"></div>
            </div>
            <div style="font-size: 12px; color: #6b7280; margin-top: 8px;">
                请稍候，正在处理您的请求
            </div>
        `;
        
        document.body.appendChild(container);
        
        return {
            show: () => {
                requestAnimationFrame(() => {
                    container.style.transform = 'translateY(0)';
                });
            },
            hide: () => {
                container.style.transform = 'translateY(100%)';
                setTimeout(() => {
                    if (container.parentNode) {
                        container.parentNode.removeChild(container);
                    }
                }, 300);
            },
            setProgress: (percent) => {
                const fill = container.querySelector('.progress-fill');
                if (fill) {
                    fill.style.width = `${Math.max(0, Math.min(100, percent))}%`;
                }
            }
        };
    }

    /**
     * 模拟进度更新
     */
    simulateProgress(progress, operationId) {
        let currentProgress = 0;
        
        const updateProgress = () => {
            if (!this.operations.has(operationId)) return;
            
            const increment = Math.random() * 15 + 5;
            currentProgress = Math.min(currentProgress + increment, 90);
            
            progress.setProgress(currentProgress);
            
            if (currentProgress < 90) {
                setTimeout(updateProgress, 200 + Math.random() * 300);
            }
        };
        
        this.operations.set(operationId, { progress: currentProgress });
        setTimeout(updateProgress, 500);
    }

    /**
     * 生成操作ID
     */
    generateOperationId() {
        return 'op_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }
}

// 初始化异步操作管理器
document.addEventListener('DOMContentLoaded', () => {
    window.asyncOps = new AsyncOperationManager();
});