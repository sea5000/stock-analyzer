import React, { useState } from 'react';
import { Copy, Check, ChevronDown, ChevronRight, Code2 } from 'lucide-react';

interface MarkdownRendererProps {
  content: string;
}

/**
 * Parses inline formatting: ***bold-italic***, **bold**, *italic*, `code`, [link](url), and raw URLs.
 */
function parseInline(text: string): React.ReactNode[] {
  // Regex tokenizing links, inline code, bold-italic, bold, italic, and URLs
  const tokenRegex = /(\*\*\*[\s\S]+?\*\*\*|\*\*[\s\S]+?\*\*|`[^`]+?`|\*[^\*]+?\*|\[[^\]]+?\]\([^\)]+?\)|https?:\/\/[^\s<)]+)/g;
  const parts = text.split(tokenRegex);

  return parts.map((part, idx) => {
    if (!part) return null;

    // Bold + Italic (***text***)
    if (part.startsWith('***') && part.endsWith('***') && part.length >= 6) {
      return (
        <strong key={idx}>
          <em>{part.slice(3, -3)}</em>
        </strong>
      );
    }

    // Bold (**text**)
    if (part.startsWith('**') && part.endsWith('**') && part.length >= 4) {
      return <strong key={idx}>{part.slice(2, -2)}</strong>;
    }

    // Inline Code (`code`)
    if (part.startsWith('`') && part.endsWith('`') && part.length >= 2) {
      return <code key={idx} className="md-inline-code">{part.slice(1, -1)}</code>;
    }

    // Italic (*text*)
    if (part.startsWith('*') && part.endsWith('*') && part.length >= 2) {
      return <em key={idx}>{part.slice(1, -1)}</em>;
    }

    // Markdown Link [title](url)
    const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (linkMatch) {
      return (
        <a key={idx} href={linkMatch[2]} target="_blank" rel="noopener noreferrer" className="md-link">
          {linkMatch[1]}
        </a>
      );
    }

    // Plain URL (https://...)
    if (/^https?:\/\//.test(part)) {
      return (
        <a key={idx} href={part} target="_blank" rel="noopener noreferrer" className="md-link">
          {part}
        </a>
      );
    }

    return part;
  });
}

/**
 * Code block component with syntax header and copy button
 */
const CodeBlock: React.FC<{ code: string; language: string }> = ({ code, language }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="md-code-block-wrapper">
      <div className="md-code-header">
        <span className="md-code-lang">
          <Code2 size={13} /> {language || 'code'}
        </span>
        <button className="md-code-copy-btn" onClick={handleCopy} title="Copy code">
          {copied ? <Check size={12} className="text-profit" /> : <Copy size={12} />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>
      <pre className="md-code-pre">
        <code>{code}</code>
      </pre>
    </div>
  );
};

/**
 * Cleans raw JSON leaks and separates model thinking/reasoning blocks.
 */
function preprocessContent(raw: string): { thought: string | null; body: string } {
  let cleaned = raw.replace(/\r\n/g, '\n').trim();

  // Extract <think>...</think> block if present
  let thought: string | null = null;
  const thinkMatch = cleaned.match(/<think>([\s\S]*?)<\/think>/i);
  if (thinkMatch) {
    thought = thinkMatch[1].trim();
    cleaned = cleaned.replace(/<think>[\s\S]*?<\/think>/i, '').trim();
  } else if (cleaned.startsWith('<think>')) {
    // In-progress stream or unclosed tag
    const endIdx = cleaned.indexOf('</think>');
    if (endIdx !== -1) {
      thought = cleaned.slice(7, endIdx).trim();
      cleaned = cleaned.slice(endIdx + 8).trim();
    }
  }

  // If text starts with raw JSON object(s) preceding markdown
  while (cleaned.startsWith('{')) {
    const endBraceIdx = cleaned.indexOf('}\n');
    if (endBraceIdx !== -1) {
      cleaned = cleaned.slice(endBraceIdx + 2).trim();
    } else {
      const mdStart = cleaned.search(/(^|\n)#{1,4}\s/);
      if (mdStart !== -1) {
        cleaned = cleaned.slice(mdStart).trim();
      } else {
        break;
      }
    }
  }

  return { thought, body: cleaned };
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
  const { thought, body } = preprocessContent(content);
  const [showThought, setShowThought] = useState(false);

  const lines = body.split('\n');
  const elements: React.ReactNode[] = [];

  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // 1. Skip completely empty lines
    if (!trimmed) {
      i++;
      continue;
    }

    // 2. Multi-line Fenced Code Block (```lang ... ```)
    if (trimmed.startsWith('```')) {
      const language = trimmed.slice(3).trim();
      const codeLines: string[] = [];
      i++; // advance past opening ```
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      if (i < lines.length) {
        i++; // advance past closing ```
      }
      elements.push(
        <CodeBlock
          key={`code_${i}`}
          code={codeLines.join('\n')}
          language={language || 'text'}
        />
      );
      continue;
    }

    // 3. Headings (#, ##, ###, ####, #####)
    const headingMatch = trimmed.match(/^(#{1,5})\s+(.*)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const headingText = headingMatch[2];
      const parsed = parseInline(headingText);

      if (level === 1) {
        elements.push(<h2 key={`h_${i}`} className="md-h1">{parsed}</h2>);
      } else if (level === 2) {
        elements.push(<h3 key={`h_${i}`} className="md-h2">{parsed}</h3>);
      } else if (level === 3) {
        elements.push(<h4 key={`h_${i}`} className="md-h3">{parsed}</h4>);
      } else {
        elements.push(<h5 key={`h_${i}`} className="md-h4">{parsed}</h5>);
      }
      i++;
      continue;
    }

    // 4. Horizontal Rule (---, ***, ___)
    if (/^[-*_]{3,}$/.test(trimmed)) {
      elements.push(<hr key={`hr_${i}`} className="md-divider" />);
      i++;
      continue;
    }

    // 5. Blockquotes (> ...)
    if (trimmed.startsWith('>')) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('>')) {
        quoteLines.push(lines[i].trim().replace(/^>\s*/, ''));
        i++;
      }
      elements.push(
        <blockquote key={`quote_${i}`} className="md-blockquote">
          {quoteLines.map((ql, qIdx) => (
            <p key={qIdx}>{parseInline(ql)}</p>
          ))}
        </blockquote>
      );
      continue;
    }

    // 6. Tables (| Header | Header | and |---|---|)
    // Tolerates lines with pipes (| ... | or ... | ...)
    const isTableLine = (l: string) => {
      const t = l.trim();
      return t.includes('|') && (t.startsWith('|') || t.split('|').length >= 2);
    };

    if (isTableLine(line) && i + 1 < lines.length && isTableLine(lines[i + 1])) {
      const rawHeader = lines[i].trim();
      i++; // advance past header

      // Split header row cells
      const headerCells = rawHeader
        .split('|')
        .map(c => c.trim())
        .filter((c, idx, arr) => (idx > 0 && idx < arr.length - 1) || c.length > 0);

      // Check for separator row (|---|---|)
      if (i < lines.length && /^\|?[-:\s|]+\|?$/.test(lines[i].trim()) && lines[i].includes('-')) {
        i++; // advance past separator
      }

      const rows: string[][] = [];
      while (i < lines.length && isTableLine(lines[i])) {
        const rowCells = lines[i]
          .trim()
          .split('|')
          .map(c => c.trim())
          .filter((c, idx, arr) => (idx > 0 && idx < arr.length - 1) || c.length > 0);
        if (rowCells.length > 0) {
          rows.push(rowCells);
        }
        i++;
      }

      elements.push(
        <div key={`table_${i}`} className="md-table-wrapper">
          <table className="md-table">
            <thead>
              <tr>
                {headerCells.map((head, hIdx) => (
                  <th key={hIdx}>{parseInline(head)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rIdx) => (
                <tr key={rIdx}>
                  {row.map((cell, cIdx) => (
                    <td key={cIdx}>{parseInline(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    // 7. Bullet Lists (- Item or * Item or + Item)
    const isBulletItem = (l: string) => /^[-*+]\s+/.test(l.trim());
    if (isBulletItem(line)) {
      const listItems: string[] = [];
      while (i < lines.length && isBulletItem(lines[i])) {
        listItems.push(lines[i].trim().replace(/^[-*+]\s+/, ''));
        i++;
      }
      elements.push(
        <ul key={`ul_${i}`} className="md-ul">
          {listItems.map((item, lIdx) => (
            <li key={lIdx}>{parseInline(item)}</li>
          ))}
        </ul>
      );
      continue;
    }

    // 8. Numbered Lists (1. Item)
    const isNumberedItem = (l: string) => /^\d+\.\s+/.test(l.trim());
    if (isNumberedItem(line)) {
      const listItems: string[] = [];
      while (i < lines.length && isNumberedItem(lines[i])) {
        listItems.push(lines[i].trim().replace(/^\d+\.\s+/, ''));
        i++;
      }
      elements.push(
        <ol key={`ol_${i}`} className="md-ol">
          {listItems.map((item, lIdx) => (
            <li key={lIdx}>{parseInline(item)}</li>
          ))}
        </ol>
      );
      continue;
    }

    // 9. Multi-line Paragraph (combine contiguous non-empty text lines into a single coherent paragraph)
    const paragraphLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() &&
      !lines[i].trim().startsWith('```') &&
      !lines[i].trim().match(/^#{1,5}\s+/) &&
      !lines[i].trim().startsWith('>') &&
      !isTableLine(lines[i]) &&
      !isBulletItem(lines[i]) &&
      !isNumberedItem(lines[i]) &&
      !/^[-*_]{3,}$/.test(lines[i].trim())
    ) {
      paragraphLines.push(lines[i].trim());
      i++;
    }

    if (paragraphLines.length > 0) {
      elements.push(
        <p key={`p_${i}`} className="md-paragraph">
          {paragraphLines.map((pl, plIdx) => (
            <React.Fragment key={plIdx}>
              {parseInline(pl)}
              {plIdx < paragraphLines.length - 1 && ' '}
            </React.Fragment>
          ))}
        </p>
      );
    }
  }

  return (
    <div className="md-container">
      {/* Optional Reasoning / Thinking foldout if model included <think> */}
      {thought && (
        <div className="md-thought-block">
          <button
            className="md-thought-toggle"
            onClick={() => setShowThought(!showThought)}
            type="button"
          >
            {showThought ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            <span>Model Reasoning Process</span>
          </button>
          {showThought && (
            <div className="md-thought-content">
              {thought}
            </div>
          )}
        </div>
      )}

      {elements}
    </div>
  );
};
