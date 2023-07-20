import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkRehype from 'remark-rehype';
import rehypeStringify from 'rehype-stringify';
import remarkGithub from 'remark-github';

export const parseGithubMarkdown = (text: string) => {
  const file = unified()
    .use(remarkParse)
    .use(remarkGfm)
    .use(remarkRehype)
    .use(remarkGithub)
    .use(rehypeStringify)
    .processSync(text);

  return file.toString();
};
