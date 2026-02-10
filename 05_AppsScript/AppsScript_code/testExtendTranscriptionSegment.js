function testExtendTranscriptionSegment() {
  const sections = {
    "warm_up": {
      "start": "00:04:15",
      "end": "00:05:58",
      "extracted_transcription": "Mentee: Oh, good afternoon...",
      "explain": "The warm-up section is designed..."
    },
    "lead-in": {
      "start": "00:12:26",
      "end": "00:12:48",
      "extracted_transcription": "Mentor: So today we need to choose...",
      "explain": "The lead-in section transitions..."
    },
    "wrap_up": {
      "start": "00:44:11",
      "end": "00:44:11",
      "extracted_transcription": "Mentee: Thank you.",
      "explain": "The wrap-up section effectively concludes..."
    }
  };
  
  const key = "warm_up"; // Thay đổi key này để lấy start và end của phần khác
  const transcriptionStr = `
[00:04:15] Mentee: 
[00:04:15] Mentee: Oh, good afternoon. 
[00:04:32] Mentor: Hello. 
[00:04:35] Mentor: Good afternoon. 
[00:04:39] Mentor: Good afternoon. 
[00:04:40] Mentor: Yeah. 
[00:04:41] Mentor: Long time no see. 
[00:04:43] Mentee: Yeah, just one week. 
[00:04:45] Mentor: Just once a week. 
[00:04:46] Mentor: Okay. 
[00:04:46] Mentor: You are drinking water. 
[00:04:50] Mentor: Okay. 
[00:04:51] Mentor: Are you good today? 
[00:04:55] Mentee: I really enjoyed our class. 
[00:04:56] Mentor: What? 
[00:05:00] Mentor: Yes, great. 
[00:05:01] Mentor: You can enjoy our class. 
[00:05:03] Mentor: I see. 
[00:05:03] Mentor: Yeah. 
[00:05:04] Mentor: So recently, I find you are quite busy with work, right? 
[00:05:13] Mentor: Mm-hmm. 
[00:05:14] Mentor: Is church starting? 
[00:05:16] Mentor: What is starting? 
[00:05:19] Mentee: I know starting busy work, just the beginning period of time. 
[00:05:25] Mentor: Mm-hmm. 
[00:05:32] Mentor: I see. 
[00:05:33] Mentor: So several times a year, you will have a period, busy period, and it starts, right? 
[00:05:42] Mentee: Yes. 
[00:05:42] Mentor: Oh, okay. 
[00:05:44] Mentor: So how long does it last? 
[00:05:48] Mentee: Hopefully, I can finish my work next week. 
[00:05:57] Mentor: Okay. 
[00:05:57] Mentor: Next week. 
[00:05:58] Mentor: Okay. 
[00:05:58] Mentor: So anyone else helps you in this period of time or only you? 
[00:06:05] Mentee: Just only me because the individual work. 
[00:06:11] Mentor: Okay. 
[00:06:14] Mentor: Yes. 
[00:06:15] Mentor: Okay. 
[00:06:16] Mentor: The task is individual and you need to work yourself, right? 
[00:06:20] Mentee: Yeah. 
[00:06:21] Mentor: Oh, interesting. 
[00:06:23] Mentee: Yeah. 
[00:06:24] Mentor: Interesting. 
[00:06:25] Mentee: Yeah. 
[00:06:27] Mentor: Yes. 
[00:06:28] Mentor: Yes, very busy. 
[00:06:28] Mentee: And just one. 
[00:06:30] Mentor: Okay. 
[00:06:31] Mentor: Is it hard for you? 
[00:06:38] Mentee: It takes a lot of time. 
[00:06:40] Mentor: Oh, I see. 
[00:06:42] Mentor: Okay. 
[00:06:42] Mentor: So how can you manage your time when you have a busy work and, you know, children? 
[00:06:53] Mentee: I think I have to fix my time for my children every day. 
[00:06:58] Mentor: Yes. 
[00:06:59] Mentee: For example, in the morning, in the afternoon, in the evening yes I just have time for my work at official hours yeah Yes. 
[00:07:15] Mentor: Okay. 
[00:07:16] Mentor: Yes. 
[00:07:17] Mentor: Office hours, right? 
[00:07:18] Mentor: Office hours. 
[00:07:20] Mentor: Oh, interesting. 
[00:07:22] Mentor: Okay. 
[00:07:22] Mentor: So you have the word office hours. 
[00:07:28] Mentor: Okay, you can only work in office hours, not in other time. 
[00:07:36] Mentor: I see. 
[00:07:36] Mentor: Right. 
[00:07:37] Mentor: So, so what kind of tasks are you working? 
[00:07:45] Mentee: Now I am working with documentation. 
[00:07:50] Mentee: A lot of, yes, official documentation for preparing . 
[00:07:59] Mentee: for preparing for preparing for preparing for preparing for preparing for preparing for preparing for preparing for preparing for preparing for preparing for preparing for preparing for preparing Yeah, annually. 
[00:08:15] Mentor: Mm hmm. 
[00:08:21] Mentor: Mm hmm. 
[00:08:23] Mentor: Is it annually or weekly or monthly? 
[00:08:26] Mentor: Annually. 
[00:08:30] Mentor: Annually. 
[00:08:33] Mentor: Yes, I see. 
[00:08:34] Mentor: Okay. 
[00:08:35] Mentor: It happens to teachers and someone who works for schools every year, right? 
[00:08:42] Mentee: Yes. 
[00:08:44] Mentor: Interesting. 
[00:08:45] Mentor: Okay. 
[00:08:46] Mentor: So I hope that you will be less busy as soon as possible. 
[00:08:51] Mentee: Yeah, I hope so. 
[00:08:52] Mentor: I hope so. 
[00:08:53] Mentor: Yeah. 
[00:08:53] Mentor: Thank you. 
[00:08:54] Mentor: Okay. 
[00:08:55] Mentor: So đoàn kiểm tra, you can use the word audit team. 
[00:09:00] Mentee: Auditive. 
[00:09:01] Mentor: Yes. 
[00:09:07] Mentor: Okay. 
[00:09:09] Mentor: Audit here, you can say with the word or inspection, inspection team. 
[00:09:18] Mentee: inspection team. 
[00:09:19] Mentor: Yes. 
[00:09:19] Mentee: Yeah. 
[00:09:22] Mentor: Okay. 
[00:09:24] Mentor: Okay. 
[00:09:25] Mentor: Inspection team. 
[00:09:26] Mentor: Okay. 
[00:09:27] Mentor: So how often does your school have inspection team? 
[00:09:33] Mentee: How often do you mean? 
[00:09:36] Mentor: How often does your school have inspection team? 
[00:09:50] Mentor: Okay. 
[00:09:50] Mentee: Once a month, yeah. 
[00:09:51] Mentor: Yes. 
[00:09:53] Mentor: Yes. 
[00:09:53] Mentor: And a busy person is you. 
[00:09:55] Mentor: Only you, right? 
[00:09:59] Mentor: Yeah. 
[00:09:59] Mentor: Okay. 
[00:10:00] Mentor: I hope you will be fine soon. 
[00:10:02] Mentor: Okay. 
[00:10:03] Mentor: Yeah. 
[00:10:08] Mentor: We talk about something more easy, easier for you. 
[00:10:09] Mentee: Mm-hmm. 
[00:10:12] Mentor: Yeah. 
[00:10:13] Mentor: To feel less stress. 
[00:10:14] Mentor: Okay. 
[00:10:16] Mentor: Yes. 
[00:10:16] Mentor: Okay. 
[00:10:17] Mentee: Yes, yes. 
[00:10:17] Mentor: So, yes. 
[00:10:18] Mentor: So first, can you tell me that do you often travel? 
[00:10:27] Mentee: I often travel once a month, just in summer. 
[00:10:32] Mentor: Really? 
[00:10:34] Mentee: Yes, just in summer. 
[00:10:35] Mentor: Yes. 
[00:10:37] Mentor: I see. 
[00:10:38] Mentee: Travel. 
[00:10:41] Mentee: Oh, I should remember that I can travel around. 
[00:10:49] Mentee: I can travel every holidays. 
[00:10:55] Mentee: Yes. 
[00:10:55] Mentor: Every holiday. 
[00:10:56] Mentor: Yes. 
[00:10:59] Mentor: Okay, so you mean you travel once a month or once a year? 
[00:11:09] Mentee: For, I think once, once every three months. 
[00:11:16] Mentor: Once three months, right? 
[00:11:18] Mentee: Yes, three months. 
[00:11:23] Mentor: Right. 
[00:11:24] Mentor: Yeah, okay, yeah. 
[00:11:26] Mentor: So I have a suggestion for you. 
[00:11:28] Mentor: Nếu mà cứ ba tháng chị đi một lần ấy, thì chị cho em every three months. 
[00:11:37] Mentee: Every three months. 
[00:11:38] Mentor: Yeah, every three months. 
[00:11:40] Mentor: Không có S à? 
[00:11:42] Mentee: Oh, yeah. 
[00:11:44] Mentor: Yes. 
[00:11:44] Mentee: I read women. 
[00:11:47] Mentor: Okay, cũng là cái chữ như vừa rồi á, thì mình có nhắc đến là every holiday, đúng không ạ? 
[00:11:53] Mentor: Rồi, nhưng mà cứ sau... Yes, đúng không? 
[00:11:54] Mentee: Oh. 
[00:11:56] Mentor: Sau every thì sẽ là danh từ số x giúp em nhé. 
[00:11:59] Mentor: Nên mình không cho s ạ. Kể cả 3 tháng ở đây thì nó cũng không có s luôn. 
[00:12:03] Mentor: Alright. 
[00:12:05] Mentor: Yes? 
[00:12:06] Mentor: Wow, okay. 
[00:12:07] Mentor: So you travel often. 
[00:12:08] Mentor: Do you enjoy traveling? 
[00:12:12] Mentee: Yes, of course. 
[00:12:14] Mentee: I enjoy my travel with my family, with my husband and children. 
[00:12:21] Mentor: Cool. 
[00:12:22] Mentee: But, yeah. 
[00:12:24] Mentee: However, actually, I have a little bit tired with my children because they are very active. 
[00:12:32] Mentor: Cool. 
[00:12:35] Mentor: yes yeah they are active they are noisy yes yes yes yes yes to be safe right To be safe. 
[00:12:37] Mentee: Yes. 
[00:12:38] Mentee: And I... Yeah, and my husband and I have to control our children and ensure them to be safe. 
[00:13:00] Mentee: Yes. 
[00:13:02] Mentor: Okay. 
[00:13:14] Mentee: Yes. 
  `;
  
  // Gọi hàm extendTranscriptionSegment với các tham số đã chuyển đổi
  const extendedTranscription = extendTranscriptionSegment(
    transcriptionStr, 
    sections, 
    key, 
    120 // extensionTime, mặc định là 120 giây
  );
  
  Logger.log(extendedTranscription);
}
