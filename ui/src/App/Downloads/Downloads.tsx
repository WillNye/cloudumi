import { FC, useEffect, useState, useMemo } from 'react';
import axios from 'core/Axios/Axios';
import { Table } from 'shared/elements/Table';
import { Segment } from 'shared/layout/Segment';
import css from './Downloads.module.css';
import { LineBreak } from 'shared/elements/LineBreak';
import { CodeBlock } from 'shared/elements/CodeBlock';
import { Link } from 'react-router-dom';

interface DownloadLink {
  download_url: string;
  os_name: string;
}

interface DownloadResponse {
  install_script: string;
  install_script_windows: string;
  download_links: DownloadLink[];
}

enum DOWNLOAD_TABS {
  LINUX_MAC = 'Linux/Mac',
  WINDOWS = 'Windows'
}

const Downloads: FC = () => {
  const [noqInstallScript, setNoqInstallScript] = useState<string>('');
  const [noqInstallScriptWindows, setNoqInstallScriptWindows] =
    useState<string>('');
  const [noqDownloadTable, setNoqDownloadTable] = useState<DownloadLink[]>([]);

  useEffect(() => {
    const fetchDownloadLinks = async () => {
      const response = await axios.get<DownloadLink[]>(
        'https://public-noq-binaries.s3.us-west-2.amazonaws.com/noq-cli/download_links/latest/download_links.json',
        { withCredentials: false }
      );
      setNoqDownloadTable(response.data);
    };

    const fetchData = async () => {
      const response = await axios.get<DownloadResponse>(
        '/api/v3/downloads/noq'
      );
      const resJson = response.data;

      setNoqInstallScript(resJson.install_script);
      setNoqInstallScriptWindows(resJson.install_script_windows);
    };

    fetchData();
    fetchDownloadLinks();
  }, []);

  const isWindows = navigator.userAgent.toLowerCase().indexOf('win') > -1;
  const [currentTab, setCurrentTab] = useState<DOWNLOAD_TABS>(
    isWindows ? DOWNLOAD_TABS.WINDOWS : DOWNLOAD_TABS.LINUX_MAC
  );

  const content = useMemo(() => {
    if (currentTab === DOWNLOAD_TABS.WINDOWS) {
      return (
        noqInstallScriptWindows && (
          <div className={css.codeBlockContainer}>
            <CodeBlock code={noqInstallScriptWindows} />
          </div>
        )
      );
    }

    return (
      noqInstallScript && (
        <div className={css.codeBlockContainer}>
          <br />
          <p className={css.description}>
            Use the command below to download and install the latest version of the
            Noq CLI. <br />
            Alternatively, you may download the binaries directly from the links
            further down on this page.
          </p>
          <CodeBlock
            code={
              '/bin/bash -c "$(curl -fsSL https://public-noq-binaries.s3.us-west-2.amazonaws.com/noq-cli/latest/install.sh)"'
            }
          />
          <p className={css.description}>
            If this is your first time using the Noq CLI, you will need to
            configure it. For your convenience, you can run the below commands
            to write your unique Noq CLI configuration.
          </p>
          <CodeBlock code={noqInstallScript} />
        </div>
      )
    );

    return (
      noqInstallScript && (
        <div className={css.codeBlockContainer}>
          <CodeBlock code={noqInstallScript} />
        </div>
      )
    );
  }, [currentTab, noqInstallScript, noqInstallScriptWindows]);

  return (
    <div className={css.container}>
      <Segment>
        <h3>Downloads</h3>
        <LineBreak />
        <p className={css.description}>
          The NOQ CLI tool makes it easy to retrieve and use AWS credentials
          securely, when paired with the NOQ Cloud platform. Download `noq` CLI
          for your operating system below, then run the following command to
          configure it:
        </p>
        <LineBreak />
        <div className={css.nav}>
          <ul className={css.navList}>
            <li
              className={`${css.navItem} ${
                currentTab === DOWNLOAD_TABS.LINUX_MAC && css.isActive
              }`}
              onClick={() => setCurrentTab(DOWNLOAD_TABS.LINUX_MAC)}
            >
              <div className={css.text}> Linux/Mac</div>
            </li>
            <li
              className={`${css.navItem} ${
                currentTab === DOWNLOAD_TABS.WINDOWS && css.isActive
              }`}
              onClick={() => setCurrentTab(DOWNLOAD_TABS.WINDOWS)}
            >
              <div className={css.text}> Windows</div>
            </li>
          </ul>
        </div>
        {content}
        {noqDownloadTable.length ? (
          <Table
            columns={[
              {
                header: 'Official Downloads (OS Name)',
                accessorKey: 'os_name',
                accessorFn: ({ download_url, os_name }) => {
                  return (
                    <Link
                      to={download_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {os_name}
                    </Link>
                  );
                }
              }
            ]}
            data={noqDownloadTable}
            spacing="expanded"
            border="row"
          />
        ) : null}
      </Segment>
    </div>
  );
};

export default Downloads;
