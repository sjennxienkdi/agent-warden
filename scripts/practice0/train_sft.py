"""practice-v0 QLoRA SFT 训练脚本（管线排练版）。

对齐 plan §5.1/§5.2 关键配方：4-bit NF4 双量化、bf16 计算、LoRA r=16 α=32
全线性投影、completion-only loss、bs=1 × 梯度累积、梯度检查点。
产物进 models/practice-v0*（隔离区，不作正式 run）。

用法：
  python scripts/practice0/train_sft.py --data data/practice0 \
      --model models/Qwen3-4B-Instruct-2507 --out models/practice-v0 --epochs 2
冒烟：加 --subset 20
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import torch
from torch.utils.data import Dataset
from transformers import (AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig,
                          Trainer, TrainingArguments)
from peft import LoraConfig, get_peft_model


def load_samples(path: Path, subset: int = 0) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    return rows[:subset] if subset else rows


def build_example(tok, row: dict, max_len: int) -> dict | None:
    msgs = [{"role": "system", "content": row["system"]},
            {"role": "user", "content": row["text"]}]
    try:
        prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True,
                                         enable_thinking=False)
    except Exception:  # 模板不支持 enable_thinking（如 2507 非思考版）
        prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    prompt_ids = tok(prompt, add_special_tokens=False)["input_ids"]
    target_ids = tok(row["target"], add_special_tokens=False)["input_ids"] + [tok.eos_token_id]
    ids = prompt_ids + target_ids
    if len(ids) > max_len:
        return None
    labels = [-100] * len(prompt_ids) + target_ids
    return {"input_ids": ids, "labels": labels}


class WindowDataset(Dataset):
    def __init__(self, tok, rows: list[dict], max_len: int) -> None:
        self.items, skipped = [], 0
        for r in rows:
            ex = build_example(tok, r, max_len)
            if ex is None:
                skipped += 1
            else:
                self.items.append(ex)
        if skipped:
            print(f"[data] skipped {skipped} windows over max_len={max_len}")

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, i: int) -> dict:
        return self.items[i]


def collate(pad_id: int):
    def _fn(batch: list[dict]) -> dict:
        n = max(len(b["input_ids"]) for b in batch)
        input_ids, labels, attn = [], [], []
        for b in batch:
            k = n - len(b["input_ids"])
            input_ids.append(b["input_ids"] + [pad_id] * k)
            labels.append(b["labels"] + [-100] * k)
            attn.append([1] * len(b["input_ids"]) + [0] * k)
        return {"input_ids": torch.tensor(input_ids), "labels": torch.tensor(labels),
                "attention_mask": torch.tensor(attn)}
    return _fn


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/practice0")
    ap.add_argument("--model", default="models/Qwen3-4B-Instruct-2507")
    ap.add_argument("--out", default="models/practice-v0")
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--ga", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=1408)
    ap.add_argument("--subset", type=int, default=0)
    args = ap.parse_args()

    assert torch.cuda.is_available(), "需要 GPU（本机 3060 6GB 或云 3090）"
    print(f"[gpu] {torch.cuda.get_device_name(0)} | torch {torch.__version__}")

    tok = AutoTokenizer.from_pretrained(args.model)
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token

    train_rows = load_samples(Path(args.data) / "train" / "windows.jsonl", args.subset)
    train_ds = WindowDataset(tok, train_rows, args.max_len)
    print(f"[data] train examples: {len(train_ds)}")

    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16)
    model = AutoModelForCausalLM.from_pretrained(
        args.model, quantization_config=bnb, device_map={"": 0},
        dtype=torch.bfloat16, attn_implementation="sdpa")
    model.config.use_cache = False
    model.gradient_checkpointing_enable()

    lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
                      task_type="CAUSAL_LM", target_modules="all-linear")
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    steps_per_epoch = math.ceil(len(train_ds) / args.ga)
    targs = TrainingArguments(
        output_dir=str(Path(args.out) / "ckpt"),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=args.ga,
        num_train_epochs=args.epochs,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_steps=max(5, int(steps_per_epoch * args.epochs * 0.03)),
        bf16=True,
        logging_steps=5,
        save_strategy="steps",
        save_steps=40,
        save_total_limit=1,
        report_to=[],
        optim="paged_adamw_8bit",
        gradient_checkpointing=True,
        dataloader_num_workers=0,
        seed=20260922,
    )
    trainer = Trainer(model=model, args=targs, train_dataset=train_ds,
                      data_collator=collate(tok.pad_token_id))
    trainer.train()

    Path(args.out).mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(Path(args.out) / "adapter"))
    tok.save_pretrained(str(Path(args.out) / "adapter"))
    (Path(args.out) / "train_config.json").write_text(json.dumps(
        {**vars(args), "train_examples": len(train_ds),
         "gpu": torch.cuda.get_device_name(0), "torch": torch.__version__},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] adapter -> {Path(args.out) / 'adapter'}")


if __name__ == "__main__":
    main()
