import { useMemo } from 'react';

interface ChatMarkdownProps {
  content: string;
}

/** 轻量 Markdown 渲染器：支持代码块、内联代码、加粗、标题、列表、链接 */
export function ChatMarkdown({ content }: ChatMarkdownProps) {
  const html = useMemo(() => renderMarkdown(content), [content]);
  return (
    <div
      className="chat-markdown prose prose-sm max-w-none break-words"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

function renderMarkdown(text: string): string {
  // 先处理代码块（```）
  const codeBlockPlaceholders: string[] = [];
  let processed = text.replace(/```(\w*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const idx = codeBlockPlaceholders.length;
    const escaped = escapeHtml(code.trimEnd());
    codeBlockPlaceholders.push(
      `<pre class="bg-gray-800 text-gray-100 rounded-lg p-3 my-2 overflow-x-auto text-xs leading-relaxed"><code class="language-${lang || ''}">${escaped}</code></pre>`
    );
    return `%%CODEBLOCK_${idx}%%`;
  });

  // 内联代码
  processed = processed.replace(/`([^`]+)`/g, (_, code) => {
    return `<code class="bg-gray-200 text-red-600 px-1 py-0.5 rounded text-xs font-mono">${escapeHtml(code)}</code>`;
  });

  // 加粗
  processed = processed.replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold">$1</strong>');

  // 斜体
  processed = processed.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // 标题 (###, ##, #)
  processed = processed.replace(/^### (.+)$/gm, '<h4 class="text-sm font-semibold mt-3 mb-1">$1</h4>');
  processed = processed.replace(/^## (.+)$/gm, '<h3 class="text-base font-semibold mt-3 mb-1">$1</h3>');
  processed = processed.replace(/^# (.+)$/gm, '<h2 class="text-lg font-semibold mt-4 mb-2">$1</h2>');

  // 无序列表
  processed = processed.replace(/^[*-] (.+)$/gm, '<li class="ml-4 list-disc">$1</li>');
  // 有序列表
  processed = processed.replace(/^\d+\. (.+)$/gm, '<li class="ml-4 list-decimal">$1</li>');

  // 将连续的 <li> 包裹为 <ul> 或 <ol>
  processed = processed.replace(/((?:<li class="ml-4 list-disc">.*?<\/li>\n?)+)/g, '<ul class="my-1">$1</ul>');
  processed = processed.replace(/((?:<li class="ml-4 list-decimal">.*?<\/li>\n?)+)/g, '<ol class="my-1">$1</ol>');

  // 链接
  processed = processed.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" class="text-primary-600 underline hover:text-primary-800" target="_blank" rel="noopener">$1</a>'
  );

  // 水平线
  processed = processed.replace(/^---+$/gm, '<hr class="my-3 border-gray-300" />');

  // 段间空行 -> <br />
  processed = processed.replace(/\n\n/g, '<br/><br/>');
  // 单行换行
  processed = processed.replace(/\n/g, '<br/>');

  // 恢复代码块
  processed = processed.replace(/%%CODEBLOCK_(\d+)%%/g, (_, idx) => {
    return codeBlockPlaceholders[parseInt(idx)] ?? '';
  });

  return processed;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
