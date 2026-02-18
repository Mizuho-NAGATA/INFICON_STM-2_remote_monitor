# Security Policy / セキュリティポリシー

## Supported Versions / サポート対象バージョン

Currently, we support the latest version available in the main branch.

現在、mainブランチの最新バージョンをサポートしています。

## Reporting a Vulnerability / 脆弱性の報告

If you discover a security vulnerability, please follow these steps:

セキュリティ脆弱性を発見した場合は、以下の手順に従ってください：

### 日本語 (Japanese)

1. **公開の Issue を作成しないでください**
   - セキュリティ問題は公開しないでください

2. **報告方法**
   - GitHub Security Advisory を使用して報告
   - または、リポジトリオーナーに直接連絡

3. **含めるべき情報**
   - 脆弱性の詳細な説明
   - 再現手順
   - 影響を受けるバージョン
   - 可能であれば修正案

### English

1. **Do NOT create a public Issue**
   - Do not disclose security issues publicly

2. **How to Report**
   - Use GitHub Security Advisory to report
   - Or contact the repository owner directly

3. **Information to Include**
   - Detailed description of the vulnerability
   - Steps to reproduce
   - Affected versions
   - Suggested fix if possible

## Security Best Practices / セキュリティのベストプラクティス

When using this software in production:

本ソフトウェアを本番環境で使用する場合：

- Keep all dependencies up to date / すべての依存関係を最新に保つ
- Use strong passwords for databases / データベースには強力なパスワードを使用
- Configure firewalls properly / ファイアウォールを適切に設定
- Use HTTPS when exposing Grafana externally / Grafanaを外部公開する場合はHTTPSを使用
- Follow your organization's security policies / 組織のセキュリティポリシーに従う
- Regularly backup your data / データを定期的にバックアップ
