import React from 'react';
import ReactDOM from 'react-dom/client';
import { Helmet, HelmetProvider } from 'react-helmet-async';
import { BrowserRouter } from 'react-router-dom';
import { DesignTokensProvider } from 'reablocks';
import { Mode, applyMode } from '@cloudscape-design/global-styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Prism from 'prismjs';

// Note: Order is important here
import 'core/utils/tracking';

import { theme } from 'shared/utils/DesignTokens';
import { ErrorBoundary } from 'shared/utils/ErrorBoundary';
import { Auth } from 'core/Auth';
import { App } from './App';
import favicon from './assets/brand/favicon.ico';
import './index.css';

import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';
import jsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker';
import cssWorker from 'monaco-editor/esm/vs/language/css/css.worker?worker';
import htmlWorker from 'monaco-editor/esm/vs/language/html/html.worker?worker';
import tsWorker from 'monaco-editor/esm/vs/language/typescript/ts.worker?worker';
import YamlWorker from './yaml.worker.js?worker';

self.MonacoEnvironment = {
  getWorker(_, label) {
    if (label === 'json') {
      return new jsonWorker();
    }
    if (label === 'css' || label === 'scss' || label === 'less') {
      return new cssWorker();
    }
    if (label === 'html' || label === 'handlebars' || label === 'razor') {
      return new htmlWorker();
    }
    if (label === 'typescript' || label === 'javascript') {
      return new tsWorker();
    }
    if (label === 'yaml' || label === 'yml') {
      return new YamlWorker();
    }
    return new editorWorker();
  }
};

Prism.languages.powershell = {
  comment: {
    pattern: /(^|[^\\])<#[\s\S]*?#>|(^|[^\\$])#.*/,
    lookbehind: true
  },
  command: {
    pattern:
      // eslint-disable-next-line max-len
      /\b(?:ls|cd|mv|cp|rm|mkdir|rmdir|touch|cat|chmod|chown|sudo|apt-get|curl|wget|ping|traceroute|ssh|scp|sftp|tail|head|less|more|find|grep|sort|cut|df|du|ps|top|nano|vim|emacs|man|killall|unzip|tar|gzip|gunzip|fgrep|wc|rev|sed|awk|date|cal|bc|expr|tee|nohup|crontab|make|gcc|python|perl|ruby|node|npm|java|javac|scala|go|rustc|swift)\b/,
    alias: 'builtin'
  },
  string: {
    pattern: /"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'/,
    greedy: true
  },
  variable: {
    pattern: /\$(?:\w+|{[^}]+})/
  },
  operator:
    // eslint-disable-next-line max-len
    /\-and|\-or|\-eq|\-neq|\-lt|\-gt|\-like|\-notlike|\-match|\-notmatch|\-contains|\-notcontains|\-in|\-notin|\-replace|!|%|\*|\+|\-|\/|::|<=|>=|<|=|>|@{|\(|\)|\{|\}|,|\[|\]|;|\?|::|\.|\$|`|@|#|\&|\||\^|~|\+=|-=|\*=|\/=|%=|\^=|\&=|\|=|<<=|>>=/,
  keyword:
    // eslint-disable-next-line max-len
    /Break|Continue|Do|Else|ElseIf|For|ForEach|If|Return|Switch|While|Until|EndForEach|EndIf|EndSwitch|EndWhile|Trap|Throw|Try|Catch|Finally|EndTry|Using|Class|Enum|EndClass|EndUsing/,
  boolean: /\$true|\$false/,
  function: {
    pattern: /(function|filter)(\s+\w+)?\s*\{/,
    inside: {
      keyword: /(function|filter)/
    }
  },
  number: /\b\d+\b/,
  punctuation: /[{}();,.]/,
  builtin:
    // eslint-disable-next-line max-len
    /\b(?:echo|print|printf|unset|export|alias|source|type|hash|pwd|cd|pushd|popd|dirs|let|declare|local|read|trap|set|shift|getopts|builtin|times|kill|jobs|stop|suspend|exit|return|exec|logout|continue|wait|help|login)\b/
};

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false
    }
  }
});

applyMode(Mode.Dark);

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <BrowserRouter>
      {/* <ApolloProvider> */}
      <QueryClientProvider client={queryClient}>
        <HelmetProvider>
          <Helmet titleTemplate="%s | Noq" defaultTitle="Noq">
            <link rel="icon" type="image/svg+xml" href={favicon} />
          </Helmet>
          <DesignTokensProvider value={theme}>
            <ErrorBoundary>
              <Auth>
                <App />
              </Auth>
            </ErrorBoundary>
          </DesignTokensProvider>
        </HelmetProvider>
        {/* </ApolloProvider> */}
      </QueryClientProvider>
    </BrowserRouter>
  </React.StrictMode>
);
