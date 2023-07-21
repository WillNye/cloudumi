import remarkGfm from 'remark-gfm';
import ReactMarkdown from 'react-markdown';
import remarkGithub from 'remark-github';
import rehypeRaw from 'rehype-raw';
import styles from './Markdown.module.css';

export const NoqMarkdown = ({ markdown }) => {
  return (
    <ReactMarkdown
      remarkPlugins={[
        // remarkBreaks,
        [remarkGfm, { singleTilde: true }],
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
        ),
        td: ({ node, ...props }) => <td className={styles.td} {...props}></td>,
        th: ({ node, ...props }) => <th className={styles.td} {...props}></th>
      }}
    >
      {markdown}
    </ReactMarkdown>
  );
};
