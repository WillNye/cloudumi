import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import ReactMarkdown from 'react-markdown';
import remarkGithub from 'remark-github';
import rehypeRaw from 'rehype-raw';
import styles from './Markdown.module.css';

export const NoqMarkdown = ({ markdown }) => {
  return (
    <ReactMarkdown
      remarkPlugins={[
        remarkBreaks,
        remarkGfm,
        [
          remarkGithub,
          { repository: 'https://github.com/noqdev/noq-templates/' }
        ]
      ]}
      rehypePlugins={[rehypeRaw]}
      remarkRehypeOptions={{ allowDangerousHtml: true }}
      components={{
        blockquote: ({ node, ...props }) => (
          <blockquote className={styles.blockquote} {...props}></blockquote>
        ),
        table: ({ node, ...props }) => (
          <table className={styles.table} {...props}></table>
        ),
        code: ({ node, ...props }) => (
          <code className={styles.code} {...props}></code>
        )
      }}
    >
      {markdown}
    </ReactMarkdown>
  );
};
