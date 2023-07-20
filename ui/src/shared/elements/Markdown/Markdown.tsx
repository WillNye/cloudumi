import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import ReactMarkdown from 'react-markdown';
import remarkGithub from 'remark-github';
import rehypeRaw from 'rehype-raw';

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
    >
      {markdown}
    </ReactMarkdown>
  );
};
