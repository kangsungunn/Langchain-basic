"""
채팅 서비스

채팅 관련 비즈니스 로직을 처리하는 서비스입니다.

😎😎 chat_service.py 서빙 관련 서비스

단순 채팅/대화형 LLM 인터페이스.

세션별 히스토리 관리, 요약, 토큰 절약 전략 등.

QLoRA 기반 파인튜닝 및 대화 지원.

"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.services.rag_service import RAGService


class ChatService:
    """채팅 서비스 클래스"""

    def __init__(self, rag_service: RAGService):
        """
        채팅 서비스를 초기화합니다.

        Args:
            rag_service: RAG 서비스 인스턴스
        """
        self.rag_service = rag_service

    def chat_rag(self, message: str) -> dict:
        """
        RAG 모드로 채팅합니다.

        Args:
            message: 사용자 메시지

        Returns:
            답변과 출처 정보가 포함된 딕셔너리
        """
        # 관련 문서 검색
        relevant_docs = self.rag_service.search_relevant_documents(message, k=3)

        if not relevant_docs:
            # 관련 문서가 없으면 일반 대화 모드
            answer = self.rag_service.generate_answer(message, context=None)
            sources = ["💬 출처: LLM (지식 베이스에 관련 문서 없음)"]
        else:
            # RAG 모드
            docs = [doc for doc, score in relevant_docs]
            context = "\n\n---\n\n".join([doc.page_content for doc in docs])
            answer = self.rag_service.generate_answer(message, context=context)

            # 출처 정보 생성
            sources = [f"📚 출처: {self.rag_service.llm.get_model_name()} + Vector DB"]
            for doc, score in relevant_docs:
                preview = doc.page_content[:80].replace("\n", " ").strip()
                if len(doc.page_content) > 80:
                    preview += "..."
                sources.append(f"{preview} (유사도: {1 - score:.2f})")

        return {
            "answer": answer,
            "sources": sources,
            "timestamp": datetime.now().isoformat(),
        }

    def chat_general(self, message: str) -> dict:
        """
        일반 대화 모드로 채팅합니다.

        Args:
            message: 사용자 메시지

        Returns:
            답변과 출처 정보가 포함된 딕셔너리
        """
        answer = self.rag_service.generate_answer(message, context=None)
        model_name = self.rag_service.llm.get_model_name()

        return {
            "answer": answer,
            "sources": [f"💬 출처: {model_name} (일반 대화 모드)"],
            "timestamp": datetime.now().isoformat(),
        }

    def load_qlora_model(
        self,
        model_name: str = "beomi/Llama-3-Open-Ko-8B",
        lora_r: int = 8,
        lora_alpha: int = 16,
        lora_dropout: float = 0.05,
        target_modules: Optional[List[str]] = None,
    ) -> tuple:
        """
        QLoRA 방식으로 모델을 로드합니다.

        Args:
            model_name: 베이스 모델 이름
            lora_r: LoRA rank
            lora_alpha: LoRA alpha
            lora_dropout: LoRA dropout
            target_modules: LoRA를 적용할 타겟 모듈

        Returns:
            (model, tokenizer) 튜플
        """
        # Lazy import for QLoRA dependencies
        try:
            import torch
            from peft import (
                LoraConfig,
                TaskType,
                get_peft_model,
                prepare_model_for_kbit_training,
            )
            from transformers import (
                AutoModelForCausalLM,
                AutoTokenizer,
                BitsAndBytesConfig,
            )
        except ImportError as e:
            raise ImportError(
                f"QLoRA 기능을 사용하려면 필요한 라이브러리를 설치하세요: "
                f"pip install torch transformers peft bitsandbytes accelerate\n"
                f"Error: {e}"
            )

        # BitsAndBytes 설정 (4bit 양자화)
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

        # 베이스 모델 로드
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
        )

        # 토크나이저 로드
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "right"

        # 학습을 위한 모델 준비
        model = prepare_model_for_kbit_training(model)

        # LoRA 설정
        if target_modules is None:
            target_modules = ["q_proj", "k_proj", "v_proj", "o_proj"]

        lora_config = LoraConfig(
            r=lora_r,
            lora_alpha=lora_alpha,
            target_modules=target_modules,
            lora_dropout=lora_dropout,
            bias="none",
            task_type=TaskType.CAUSAL_LM,
        )

        # PEFT 모델 생성
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()

        return model, tokenizer

    def chat_with_qlora_model(
        self,
        model,
        tokenizer,
        message: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
    ) -> dict:
        """
        QLoRA 모델로 대화합니다.

        Args:
            model: QLoRA 모델
            tokenizer: 토크나이저
            message: 사용자 메시지
            max_new_tokens: 생성할 최대 토큰 수
            temperature: 온도 (다양성 조절)
            top_p: Top-p 샘플링

        Returns:
            답변과 정보가 포함된 딕셔너리
        """
        import torch

        # 프롬프트 구성
        prompt = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

당신은 친절하고 유용한 AI 어시스턴트입니다.<|eot_id|><|start_header_id|>user<|end_header_id|>

{message}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""

        # 토크나이징
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

        # 생성
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )

        # 디코딩
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # 응답 부분만 추출
        answer = generated_text.split("assistant")[-1].strip()

        return {
            "answer": answer,
            "sources": ["🤖 출처: QLoRA Fine-tuned Model"],
            "timestamp": datetime.now().isoformat(),
            "model_info": {
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_new_tokens,
            },
        }

    def prepare_training_dataset(
        self, tokenizer, conversations: List[Dict[str, str]], max_length: int = 512
    ):
        """
        학습 데이터셋을 준비합니다.

        Args:
            tokenizer: 토크나이저
            conversations: [{"prompt": "질문", "response": "답변"}, ...] 형식의 대화 리스트
            max_length: 최대 시퀀스 길이

        Returns:
            준비된 Dataset 객체
        """
        try:
            from datasets import Dataset  # type: ignore
        except ImportError:
            raise ImportError("datasets 라이브러리가 필요합니다: pip install datasets")

        def format_prompt(prompt: str, response: str) -> str:
            """프롬프트 포맷팅"""
            return f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

당신은 친절하고 유용한 AI 어시스턴트입니다.<|eot_id|><|start_header_id|>user<|end_header_id|>

{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

{response}<|eot_id|>"""

        # 데이터 포맷팅
        formatted_data = []
        for conv in conversations:
            text = format_prompt(conv["prompt"], conv["response"])
            formatted_data.append({"text": text})

        # Dataset 생성
        dataset = Dataset.from_list(formatted_data)

        # 토크나이징 함수
        def tokenize_function(examples):
            return tokenizer(
                examples["text"],
                truncation=True,
                max_length=max_length,
                padding="max_length",
            )

        # 토크나이징 적용
        tokenized_dataset = dataset.map(
            tokenize_function, batched=True, remove_columns=dataset.column_names
        )

        return tokenized_dataset

    def train_qlora_model(
        self,
        model,
        tokenizer,
        train_dataset,
        output_dir: str = "./checkpoints/qlora",
        num_train_epochs: int = 3,
        per_device_train_batch_size: int = 4,
        gradient_accumulation_steps: int = 4,
        learning_rate: float = 2e-4,
        warmup_steps: int = 100,
        logging_steps: int = 10,
        save_steps: int = 100,
    ) -> Dict[str, Any]:
        """
        QLoRA 모델을 학습합니다.

        Args:
            model: QLoRA 모델
            tokenizer: 토크나이저
            train_dataset: 학습 데이터셋
            output_dir: 체크포인트 저장 경로
            num_train_epochs: 에폭 수
            per_device_train_batch_size: 배치 크기
            gradient_accumulation_steps: 그래디언트 누적 스텝
            learning_rate: 학습률
            warmup_steps: 워밍업 스텝
            logging_steps: 로깅 주기
            save_steps: 저장 주기

        Returns:
            학습 결과 정보
        """
        try:
            from transformers import Trainer, TrainingArguments
        except ImportError:
            raise ImportError(
                "transformers 라이브러리가 필요합니다: pip install transformers"
            )

        # 학습 설정
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=num_train_epochs,
            per_device_train_batch_size=per_device_train_batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            learning_rate=learning_rate,
            warmup_steps=warmup_steps,
            logging_steps=logging_steps,
            save_steps=save_steps,
            save_total_limit=3,
            fp16=True,
            optim="paged_adamw_8bit",
            report_to="none",
        )

        # Trainer 생성
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            tokenizer=tokenizer,  # type: ignore
        )

        # 학습 시작
        print("🚀 QLoRA 학습 시작...")
        train_result = trainer.train()

        # 모델 저장
        final_model_path = os.path.join(output_dir, "final_model")
        trainer.save_model(final_model_path)
        tokenizer.save_pretrained(final_model_path)

        print(f"✅ 학습 완료! 모델 저장 위치: {final_model_path}")

        return {
            "status": "completed",
            "output_dir": output_dir,
            "final_model_path": final_model_path,
            "train_loss": train_result.training_loss,
            "epochs": num_train_epochs,
            "timestamp": datetime.now().isoformat(),
        }

    def load_trained_qlora_model(
        self, base_model_name: str, adapter_path: str
    ) -> tuple:
        """
        학습된 QLoRA 어댑터를 로드합니다.

        Args:
            base_model_name: 베이스 모델 이름
            adapter_path: 어댑터 경로

        Returns:
            (model, tokenizer) 튜플
        """
        try:
            import torch
            from peft import PeftModel
            from transformers import (
                AutoModelForCausalLM,
                AutoTokenizer,
                BitsAndBytesConfig,
            )
        except ImportError as e:
            raise ImportError(
                f"QLoRA 기능을 사용하려면 필요한 라이브러리를 설치하세요: "
                f"pip install torch transformers peft bitsandbytes accelerate\n"
                f"Error: {e}"
            )

        # BitsAndBytes 설정
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

        # 베이스 모델 로드
        model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
        )

        # 어댑터 로드
        model = PeftModel.from_pretrained(model, adapter_path)

        # 토크나이저 로드
        tokenizer = AutoTokenizer.from_pretrained(adapter_path, trust_remote_code=True)
        tokenizer.pad_token = tokenizer.eos_token

        print(f"✅ QLoRA 모델 로드 완료: {adapter_path}")

        return model, tokenizer
