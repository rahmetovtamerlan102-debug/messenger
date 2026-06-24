package com.example.messenger

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.messenger.adapters.ChatAdapter
import com.example.messenger.databinding.ActivityChatListBinding
import com.example.messenger.models.Chat
import com.example.messenger.network.ApiClient
import com.example.messenger.utils.TokenManager
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class ChatListActivity : AppCompatActivity() {
    private lateinit var binding: ActivityChatListBinding
    private lateinit var tokenManager: TokenManager
    private lateinit var adapter: ChatAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityChatListBinding.inflate(layoutInflater)
        setContentView(binding.root)

        tokenManager = TokenManager(this)
        if (tokenManager.getAccessToken() == null) {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
            return
        }

        binding.rvChats.layoutManager = LinearLayoutManager(this)
        adapter = ChatAdapter(emptyList()) { chat ->
            val intent = Intent(this, ChatActivity::class.java)
            intent.putExtra("chatId", chat.id.toString())
            intent.putExtra("chatName", chat.name ?: "Чат")
            startActivity(intent)
        }
        binding.rvChats.adapter = adapter

        loadChats()
    }

    private fun loadChats() {
        val token = tokenManager.getAccessToken() ?: return
        ApiClient.getApiService(this).getChats("Bearer $token")
            .enqueue(object : Callback<List<Chat>> {
                override fun onResponse(call: Call<List<Chat>>, response: Response<List<Chat>>) {
                    if (response.isSuccessful) {
                        val chats = response.body() ?: emptyList()
                        adapter = ChatAdapter(chats) { chat ->
                            val intent = Intent(this@ChatListActivity, ChatActivity::class.java)
                            intent.putExtra("chatId", chat.id.toString())
                            intent.putExtra("chatName", chat.name ?: "Чат")
                            startActivity(intent)
                        }
                        binding.rvChats.adapter = adapter
                    }
                }

                override fun onFailure(call: Call<List<Chat>>, t: Throwable) {
                    Toast.makeText(this@ChatListActivity, "Ошибка загрузки", Toast.LENGTH_SHORT).show()
                }
            })
    }
}
