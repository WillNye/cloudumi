import ResourcesTable from './components/ResourcesTable';
import css from './Resources.module.css';

const Resources = () => {
  return (
    <div className={css.container}>
      <h3 className={css.header}>Resources</h3>
      <div className={css.tableContainer}>
        <ResourcesTable />
      </div>
    </div>
  );
};

export default Resources;
