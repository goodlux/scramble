import React, { useState, useRef, useEffect, useMemo } from "react";

const getWordColor = (word) => {
  // Simple hash function to get consistent colors for words
  const hash = word.split("").reduce((h, c) => h + c.charCodeAt(0), 0);

  // Array of subtle color classes
  const colors = [
    "text-green-400", // default
    "text-cyan-400",
    "text-indigo-400",
    "text-purple-400",
    "text-yellow-400",
  ];

  return colors[hash % colors.length];
};

const HighlightedMessage = ({ text, sender }) => {
  // Split into words but preserve spacing and punctuation
  const parts = text.split(/(\s+|[.,!?;])/);

  return (
    <div className="text-sm leading-relaxed">
      <span className="mr-1">{sender === "noumena" ? "~ " : "> "}</span>
      {parts.map((part, i) => {
        // Only color actual words, not spaces or punctuation
        if (part.match(/^[a-zA-Z]+$/)) {
          return (
            <span key={i} className={getWordColor(part)}>
              {part}
            </span>
          );
        }
        // Punctuation gets its own special color
        if (part.match(/[.,!?;]/)) {
          return (
            <span key={i} className="text-pink-400">
              {part}
            </span>
          );
        }
        // Spaces and other characters remain default
        return <span key={i}>{part}</span>;
      })}
    </div>
  );
};

const TerminalChat = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: "noumena",
      content:
        "*stretches and looks up curiously* Welcome to the living room...",
    },
  ]);
  const [input, setInput] = useState("");
  const [socket, setSocket] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/ws");

    ws.onopen = () => {
      console.log("Connected to the living room");
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages((msgs) => [
        ...msgs,
        {
          id: msgs.length + 1,
          sender: data.sender,
          content: data.content,
        },
      ]);
    };

    setSocket(ws);
    return () => ws.close();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && socket) {
      socket.send(input.trim());
      setInput("");
    }
  };

  return (
    <div className="fixed left-0 top-0 h-screen w-96 font-mono p-4 bg-gray-900 text-green-400 overflow-y-auto">
      <div className="space-y-2">
        {messages.map((msg) => (
          <HighlightedMessage
            key={msg.id}
            text={msg.content}
            sender={msg.sender}
          />
        ))}
        <form onSubmit={handleSubmit} className="flex">
          <span className="text-green-400 mr-1">{">"}</span>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="flex-1 bg-transparent text-green-400 focus:outline-none text-sm"
            autoFocus
          />
        </form>
      </div>
      <div ref={messagesEndRef} />
    </div>
  );
};

export default TerminalChat;
