import axios from 'core/Axios/Axios';

export async function getMonacoCompletions(model, position, monaco) {
  let resource = false;
  let action = false;
  const lines = model.getLinesContent();

  for (let i = position.lineNumber - 1; i >= 0; i--) {
    if (lines[i].indexOf('resource:') > -1) {
      resource = true;
      break;
    }

    if (lines[i].indexOf('action:') > -1) {
      action = true;
      break;
    }

    if (lines[i].indexOf('sid:') > -1) {
      return { suggestions: [] };
    }
  }
  const lastLine = model.getLineContent(position.lineNumber);
  const prefix = lastLine
    .trim()
    .replace(/"/g, '')
    .replace(/'/g, '')
    .replace(/- /g, '')
    .replace(/-/g, '')
    .replace(/action:/g, '')
    .replace(/resource:/g, '')
    .replace(/,/g, '')
    .replace(' ', '')
    .replace(/\[/, '')
    .replace(/]/, '');
  // prefixRange is the range of the prefix that will be replaced if someone selects the suggestion
  const prefixRange = model.findPreviousMatch(prefix, position);
  const defaultWordList = [];
  if (prefix === '' || prefix.indexOf('-') > -1) {
    return { suggestions: [] };
  }
  if (action === true) {
    const res = await axios.get(
      '/api/v1/policyuniverse/autocomplete?prefix=' + prefix
    );

    const wordList = res.data;

    if (!wordList) {
      return { suggestions: defaultWordList };
    }

    if (!prefixRange) {
      return { suggestions: defaultWordList };
    }

    const suggestedWordList = wordList.map(ea => ({
      label: ea.permission,
      insertText: ea.permission,
      kind: monaco.languages.CompletionItemKind.Property,
      range: prefixRange.range
    }));

    return { suggestions: suggestedWordList };
    // TODO: error handling other than returning empty list ?
  } else if (resource === true) {
    const res = await axios.get(
      '/api/v2/typeahead/resources?typeahead=' + prefix
    );

    const wordList = res.data;

    if (!wordList) {
      return { suggestions: defaultWordList };
    }

    const suggestedWordList = wordList.map(ea => ({
      label: ea,
      insertText: ea,
      kind: monaco.languages.CompletionItemKind.Function,
      range: prefixRange.range
    }));
    return { suggestions: suggestedWordList };
    // TODO: error handling other than returning empty list ?
  }
  return { suggestions: defaultWordList };
}

export function getMonacoTriggerCharacters() {
  const lowerCase = 'abcdefghijklmnopqrstuvwxyz';
  return (lowerCase + lowerCase.toUpperCase() + '0123456789_-:').split('');
}
