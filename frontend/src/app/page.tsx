'use client'

import { useState, useRef, useEffect } from 'react'
import styles from './page.module.css'

type Message = {
  content: string
  isUser: boolean
  sources?: string[]
  timestamp: string
}

type ChatMode = 'rag' | 'general'
type Model = 'openai' | 'midm'

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [chatMode, setChatMode] = useState<ChatMode>('rag')
  const [model, setModel] = useState<Model>('openai')
  const [expandedSources, setExpandedSources] = useState<Set<number>>(new Set())
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!inputValue.trim() || isLoading) return

    const userMessage: Message = {
      content: inputValue,
      isUser: true,
      timestamp: new Date().toISOString(),
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)

    try {
      const endpoint = chatMode === 'rag' ? '/api/chat/rag' : '/api/chat/general'
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: inputValue, model }),
      })

      if (!response.ok) {
        throw new Error('서버 오류가 발생했습니다.')
      }

      const data = await response.json()

      const botMessage: Message = {
        content: data.answer,
        isUser: false,
        sources: data.sources,
        timestamp: data.timestamp,
      }

      setMessages(prev => [...prev, botMessage])
    } catch (error) {
      const errorMessage: Message = {
        content: '죄송합니다. 오류가 발생했습니다: ' + (error as Error).message,
        isUser: false,
        timestamp: new Date().toISOString(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const sendExampleQuestion = (question: string) => {
    setInputValue(question)
  }

  const toggleSources = (index: number) => {
    setExpandedSources(prev => {
      const newSet = new Set(prev)
      if (newSet.has(index)) {
        newSet.delete(index)
      } else {
        newSet.add(index)
      }
      return newSet
    })
  }

  return (
    <div className={styles.container}>
      <div className={styles.chatContainer}>
        <div className={styles.chatHeader}>
          <h1>AI Chat</h1>
          <p>Ask me anything</p>

          <div className={styles.modeSelector}>
            <button
              className={`${styles.modeButton} ${chatMode === 'rag' ? styles.active : ''}`}
              onClick={() => setChatMode('rag')}
            >
              📚 Knowledge Base
              <span className={styles.modeDescription}>RAG Mode</span>
            </button>
            <button
              className={`${styles.modeButton} ${chatMode === 'general' ? styles.active : ''}`}
              onClick={() => setChatMode('general')}
            >
              💬 General
              <span className={styles.modeDescription}>Free Chat</span>
            </button>
          </div>

          <div className={styles.modelSelector}>
            <span className={styles.modelLabel}>Model:</span>
            <button
              className={`${styles.modelButton} ${model === 'openai' ? styles.activeModel : ''}`}
              onClick={() => setModel('openai')}
            >
              🤖 OpenAI
            </button>
            <button
              className={`${styles.modelButton} ${model === 'midm' ? styles.activeModel : ''}`}
              onClick={() => setModel('midm')}
            >
              🦙 Midm
            </button>
          </div>
        </div>

        <div className={styles.chatMessages}>
          {messages.length === 0 && (
            <>
              <div className={styles.messageBot}>
                <div className={styles.messageAvatar}>🤖</div>
                <div className={styles.messageContent}>
                  ㅎㅇ
                </div>
              </div>

              <div className={styles.exampleQuestions}>
                <button className={styles.exampleBtn} onClick={() => sendExampleQuestion('LangChain이 뭐야?')}>
                  LangChain
                </button>
                <button className={styles.exampleBtn} onClick={() => sendExampleQuestion('RAG가 뭐고 어떻게 작동해?')}>
                  RAG 설명
                </button>
                <button className={styles.exampleBtn} onClick={() => sendExampleQuestion('PGVector를 사용하는 이유는?')}>
                  PGVector 이유
                </button>
                <button className={styles.exampleBtn} onClick={() => sendExampleQuestion('안녕! 오늘 기분 어때?')}>
                  일상 대화
                </button>
              </div>
            </>
          )}

          {messages.map((message, index) => (
            <div
              key={index}
              className={message.isUser ? styles.messageUser : styles.messageBot}
            >
              {!message.isUser && <div className={styles.messageAvatar}>🤖</div>}
              <div className={styles.messageContentWrapper}>
                <div className={styles.messageContent}>
                  {message.content}
                </div>
                {message.sources && message.sources.length > 0 && !message.isUser && (
                  <div className={styles.sourcesContainer}>
                    <button
                      className={styles.sourcesToggle}
                      onClick={() => toggleSources(index)}
                    >
                      {expandedSources.has(index) ? '📚 출처 숨기기 ▲' : '📚 출처 보기 ▼'}
                    </button>
                    {expandedSources.has(index) && (
                      <div className={styles.sources}>
                        {message.sources.map((source, idx) => (
                          <div key={idx} className={styles.sourceItem}>
                            {source}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
              {message.isUser && <div className={styles.messageAvatar}>👤</div>}
            </div>
          ))}

          {isLoading && (
            <div className={styles.messageBot}>
              <div className={styles.messageAvatar}>🤖</div>
              <div className={styles.messageContent}>
                <div className={styles.loading}>
                  <div className={styles.loadingDot}></div>
                  <div className={styles.loadingDot}></div>
                  <div className={styles.loadingDot}></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className={styles.chatInputContainer}>
          <form className={styles.chatInputForm} onSubmit={sendMessage}>
            <input
              type="text"
              className={styles.chatInput}
              placeholder="메시지를 입력하세요..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              disabled={isLoading}
            />
            <button
              type="submit"
              className={styles.chatSendBtn}
              disabled={isLoading || !inputValue.trim()}
            >
              전송
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}

