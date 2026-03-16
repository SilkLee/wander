import * as fs from 'fs';
import * as path from 'path';

describe('Vite dev server setup', () => {
  const frontendRoot = path.resolve(__dirname, '..');

  describe('vite.config.ts', () => {
    const configPath = path.join(frontendRoot, 'vite.config.ts');

    it('exists', () => {
      expect(fs.existsSync(configPath)).toBe(true);
    });

    it('configures host 0.0.0.0 and port 5173', () => {
      const content = fs.readFileSync(configPath, 'utf-8');
      expect(content).toContain("host: '0.0.0.0'");
      expect(content).toContain('port: 5173');
    });

    it('proxies /api to http://localhost:8002', () => {
      const content = fs.readFileSync(configPath, 'utf-8');
      expect(content).toContain("'/api'");
      expect(content).toContain("target: 'http://localhost:8002'");
    });

    it('uses @vitejs/plugin-react', () => {
      const content = fs.readFileSync(configPath, 'utf-8');
      expect(content).toContain('@vitejs/plugin-react');
      expect(content).toContain('react()');
    });
  });

  describe('index.html', () => {
    const htmlPath = path.join(frontendRoot, 'index.html');

    it('exists', () => {
      expect(fs.existsSync(htmlPath)).toBe(true);
    });

    it('has a div with id root', () => {
      const content = fs.readFileSync(htmlPath, 'utf-8');
      expect(content).toContain('id="root"');
    });

    it('references src/main.tsx as script', () => {
      const content = fs.readFileSync(htmlPath, 'utf-8');
      expect(content).toContain('src/main.tsx');
    });
  });

  describe('src/main.tsx', () => {
    const mainPath = path.join(frontendRoot, 'src', 'main.tsx');

    it('exists', () => {
      expect(fs.existsSync(mainPath)).toBe(true);
    });

    it('imports and renders App', () => {
      const content = fs.readFileSync(mainPath, 'utf-8');
      expect(content).toContain("from './App'");
      expect(content).toContain('createRoot');
    });

    it('mounts to #root element', () => {
      const content = fs.readFileSync(mainPath, 'utf-8');
      expect(content).toContain("getElementById('root')");
    });
  });

  describe('package.json', () => {
    it('has vite as devDependency', () => {
      const pkg = JSON.parse(
        fs.readFileSync(path.join(frontendRoot, 'package.json'), 'utf-8')
      );
      expect(pkg.devDependencies).toHaveProperty('vite');
    });

    it('has @vitejs/plugin-react as devDependency', () => {
      const pkg = JSON.parse(
        fs.readFileSync(path.join(frontendRoot, 'package.json'), 'utf-8')
      );
      expect(pkg.devDependencies).toHaveProperty('@vitejs/plugin-react');
    });

    it('has dev script using vite', () => {
      const pkg = JSON.parse(
        fs.readFileSync(path.join(frontendRoot, 'package.json'), 'utf-8')
      );
      expect(pkg.scripts.dev).toBe('vite');
    });

    it('has build script using vite build', () => {
      const pkg = JSON.parse(
        fs.readFileSync(path.join(frontendRoot, 'package.json'), 'utf-8')
      );
      expect(pkg.scripts.build).toBe('vite build');
    });
  });
});
