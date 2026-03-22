---
name: star-ccm-basics
description: "STAR-CCM+ Java/Python マクロ開発の基礎知識"
---

# STAR-CCM+ マクロ開発スキル

## When to use（このスキルが有効な場面）
- ユーザーが STAR-CCM+ のマクロ作成を依頼した場合
- メッシュ生成、境界条件、物性値設定の質問を受けた場合
- シミュレーション結果の後処理を依頼された場合

## 基本ルール

1. **必ず doc_search を先に行う** — APIクラス名は覚えていても正確な引数は検索して確認する
2. **完全なマクロを書く** — 断片コードではなく、そのまま実行できるコードを書く
3. **エラーが出たら log_read** — 推測で修正しない。ログを読んでから直す

## STAR-CCM+ Java マクロの基本構造

```java
// STAR-CCM+ 18.x 対応
import star.common.*;
import star.base.neo.*;

public class MacroName extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        // ここに処理を書く
    }
}
```

## よく使うクラス

| クラス | 用途 |
|--------|------|
| `Simulation` | シミュレーション全体へのアクセス |
| `MeshPipelineController` | メッシュ生成パイプライン |
| `AutoMeshOperation` | 自動メッシュ操作 |
| `PolyhederalMesher` | ポリヘドラルメッシャー |
| `PrismLayerMesher` | プリズム層メッシャー |
| `PhysicsContinuum` | 物理モデル設定 |
| `BoundaryCondition` | 境界条件設定 |
| `ResidualMonitor` | 残差モニター |

## メッシュ生成の典型的なコード

```java
// メッシュ生成の基本パターン
MeshPipelineController mpc = sim.get(MeshPipelineController.class);
mpc.generateVolumeMesh();
```

## エラー対応フロー

```
エラー発生
  → log_read でエラーメッセージを確認
  → doc_search でAPI仕様を確認
  → コードを修正
  → star_execute で再実行
  → 解決したら memory_write で記録
```
