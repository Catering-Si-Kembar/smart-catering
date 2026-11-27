'use client';

import { useRef, useState, type FormEvent } from 'react';
import PersonOutlineRoundedIcon from '@mui/icons-material/PersonOutlineRounded';
import SendRoundedIcon from '@mui/icons-material/SendRounded';
import SupportAgentRoundedIcon from '@mui/icons-material/SupportAgentRounded';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface ChatMessage {
  readonly id: string;
  readonly sender: 'user' | 'assistant';
  readonly text: string;
  readonly sourceLabel?: string;
}

const QUICK_PROMPTS = [
  'Berapa bahan untuk 100 box Ayam Goreng Lengkuas?',
  'Pesanan besok tanggal 25 Nov apa saja?',
  'Apa aturan minimal DP katering?',
] as const;

const INITIAL_MESSAGES: readonly ChatMessage[] = [
  {
    id: 'msg-1',
    sender: 'assistant',
    text: 'Halo! Saya Asisten Operasional Catering Si Kembar. Pilih pertanyaan cepat di bawah atau ketik pertanyaan seputar resep takaran baku, SOP dapur, atau jadwal pesanan.',
    sourceLabel: 'Asisten Dapur',
  },
];

function buildSimulatedReply(question: string): { text: string; sourceLabel: string } {
  const lower = question.toLowerCase();
  if (lower.includes('100') || lower.includes('bahan') || lower.includes('lengkuas')) {
    return {
      text: 'Untuk 100 porsi Nasi Box Ayam Goreng Lengkuas: Beras Putih 15 kg, Ayam Potong 12,5 kg, Lengkuas Parut 2 kg, Minyak Goreng 3 liter, dan Daun Salam 100 lembar.',
      sourceLabel: 'Sumber: Resep Standar Dapur',
    };
  }
  if (lower.includes('besok') || lower.includes('jadwal') || lower.includes('pesanan')) {
    return {
      text: 'Jadwal pesanan 25 Nov 2026: (1) 09:30 WIB - 100 Box Ayam Goreng Lengkuas (Sedang Dimasak); (2) 11:30 WIB - 50 Box Rendang Daging (Siap Dikirim).',
      sourceLabel: 'Sumber: Data Pesanan Aktif',
    };
  }
  if (lower.includes('dp') || lower.includes('bayar') || lower.includes('aturan')) {
    return {
      text: 'Sesuai SOP Catering Si Kembar, DP minimal adalah 60% dari total nilai pesanan sebelum pesanan masuk ke antrean jadwal masak dapur.',
      sourceLabel: 'Sumber: SOP Operasional Katering',
    };
  }
  return {
    text: 'Pertanyaan di luar konteks operasional katering belum dapat dijawab. Silakan tanyakan seputar menu, bahan baku, SOP uang muka, atau jadwal pesanan.',
    sourceLabel: 'Bantuan Operasional',
  };
}

export default function ChatPage() {
  const [messages, setMessages] = useState<readonly ChatMessage[]>(INITIAL_MESSAGES);
  const [draft, setDraft] = useState('');
  const nextIdRef = useRef(2);

  const sendQuestion = (questionText: string) => {
    const trimmed = questionText.trim();
    if (!trimmed) return;

    const reply = buildSimulatedReply(trimmed);
    const userMsgId = nextIdRef.current;
    nextIdRef.current += 2;
    setMessages((prev) => [
      ...prev,
      { id: `u-${userMsgId}`, sender: 'user', text: trimmed },
      {
        id: `a-${userMsgId + 1}`,
        sender: 'assistant',
        text: reply.text,
        sourceLabel: reply.sourceLabel,
      },
    ]);
    setDraft('');
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    sendQuestion(draft);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-950">
          Asisten AI Catering Si Kembar
        </h1>
        <p className="text-base text-slate-700">
          Asisten pintar untuk membantu staf dapur dan pengelola mengecek resep takaran baku, SOP,
          serta jadwal pengiriman pesanan secara cepat.
        </p>
      </div>

      <Card className="border-[#dad9d6]">
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">Pertanyaan Cepat</CardTitle>
          <CardDescription className="text-sm text-slate-700">
            Ketuk salah satu tombol agar staf senior tidak perlu mengetik panjang.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          {QUICK_PROMPTS.map((prompt) => (
            <Button
              key={prompt}
              type="button"
              variant="outline"
              onClick={() => sendQuestion(prompt)}
              className="h-auto whitespace-normal py-2.5 text-left border-[#dad9d6] bg-white hover:bg-[#f9f9f8]"
            >
              {prompt}
            </Button>
          ))}
        </CardContent>
      </Card>

      <Card className="border-[#dad9d6]">
        <CardContent className="space-y-4 p-4 sm:p-6">
          <div
            className="space-y-3"
            aria-live="polite"
            aria-label="Riwayat percakapan asisten katering"
          >
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={
                  msg.sender === 'user'
                    ? 'ml-auto max-w-xl rounded-2xl bg-primary p-4 text-primary-foreground font-medium shadow-sm'
                    : 'mr-auto max-w-2xl rounded-2xl border border-[#dad9d6] bg-[#f9f9f8] p-4 text-slate-950'
                }
              >
                <div className="mb-1.5 flex items-center gap-2 text-xs font-bold">
                  {msg.sender === 'user' ? (
                    <>
                      <PersonOutlineRoundedIcon sx={{ fontSize: 18 }} aria-hidden={true} />
                      <span>Anda</span>
                    </>
                  ) : (
                    <>
                      <SupportAgentRoundedIcon
                        sx={{ fontSize: 18 }}
                        className="text-[#5c3271]"
                        aria-hidden={true}
                      />
                      <span className="text-[#5c3271]">Asisten Smart Catering</span>
                    </>
                  )}
                </div>
                <p className="text-base leading-relaxed">{msg.text}</p>
                {msg.sourceLabel ? (
                  <Badge
                    variant="outline"
                    className="mt-2.5 border-slate-400 bg-white text-xs font-semibold text-slate-800"
                  >
                    {msg.sourceLabel}
                  </Badge>
                ) : null}
              </div>
            ))}
          </div>

          <form
            onSubmit={handleSubmit}
            className="flex flex-col gap-2.5 border-t border-slate-200 pt-4 sm:flex-row"
          >
            <label htmlFor="chat-input" className="sr-only">
              Tulis pertanyaan untuk asisten
            </label>
            <input
              id="chat-input"
              type="text"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Tulis pertanyaan tentang menu, resep, atau jadwal..."
              className="min-h-12 flex-1 rounded-xl border border-slate-400 bg-white px-4 text-base text-slate-950 focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring"
            />
            <Button type="submit" size="lg" className="shrink-0">
              <SendRoundedIcon sx={{ fontSize: 18 }} aria-hidden={true} />
              Kirim Pesan
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
