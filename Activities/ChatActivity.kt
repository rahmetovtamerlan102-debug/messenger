package com.example.messenger

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.messenger.adapters.MessageAdapter
import com.example.messenger.databinding.ActivityChatBinding
import com.example.messenger.models.Message
import com.example.messenger.models.Page
import com.example.messenger.models.User
import com.example.messenger.network.ApiClient
import com.example.messenger.network.WebSocketManager
import com.example.messenger.utils.TokenManager
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.util.UUID

class ChatActivity : AppCompatActivity() {
    private lateinit var binding: ActivityChatBinding
    private lateinit var tokenManager: TokenManager
    private lateinit var webSocketManager: WebSocketManager
    private lateinit var adapter: MessageAdapter
    private val messages = mutableListOf<Message>()
    private var chatId: UUID? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityChatBinding.inflate(layoutInflater)
        setContentView(binding.root)

        tokenManager = TokenManager(this)
        val token = tokenManager.getAccessToken()
        if (token == null) {
            finish()
            return
        }

        chatId = UUID.fromString(intent.getStringExtra("chatId"))
        val chatName = intent.getStringExtra("chatName") ?: "Чат"
        supportActionBar?.title = chatName

        binding.rvMessages.layoutManager = LinearLayoutManager(this)
        adapter = MessageAdapter(messages)
        binding.rvMessages.adapter = adapter

        val listener = object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: okhttp3.Response) {
                runOnUiThread { Toast.makeText(this@ChatActivity, "Подключено", Toast.LENGTH_SHORT).show() }
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                val json = JSONObject(text)
                val type = json.optString("type")
                when (type) {
                    "message" -> {
                        val sender = User(id = 0, username = json.getString("sender"))
                        val msg = Message(
                            id = UUID.randomUUID(),
                            chat = chatId!!,
                            sender = sender,
                            text = json.getString("message"),
                            mediaUrl = json.optString("media_url", ""),
                            mediaType = "",
                            timestamp = json.getString("timestamp"),
                            updatedAt = json.getString("timestamp"),
                            isDeleted = false,
                            reactions = emptyMap()
                        )
                        runOnUiThread {
                            messages.add(msg)
                            adapter.notifyItemInserted(messages.size - 1)
                            binding.rvMessages.scrollToPosition(messages.size - 1)
                        }
                    }
                    "reaction_update" -> {
                        // обновить реакции
                    }
                    "pin_update" -> {
                        // обновить закреп
                    }
                    "delete_update" -> {
                        // удалить сообщение
                    }
                    "typing" -> {
                        // показать индикатор печатания
                    }
                }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: okhttp3.Response?) {
                runOnUiThread { Toast.makeText(this@ChatActivity, "Ошибка WebSocket", Toast.LENGTH_SHORT).show() }
            }
        }

        webSocketManager = WebSocketManager(listener, token)
        webSocketManager.connect(chatId.toString())

        loadMessages(chatId!!)

        binding.btnSend.setOnClickListener {
            val text = binding.etMessage.text.toString().trim()
            if (text.isNotEmpty()) {
                webSocketManager.sendMessage(text)
                binding.etMessage.text.clear()
            }
        }
    }

    private fun loadMessages(chatId: UUID) {
        val token = tokenManager.getAccessToken() ?: return
        ApiClient.getApiService(this).getMessages("Bearer $token", chatId)
            .enqueue(object : Callback<Page<Message>> {
                override fun onResponse(call: Call<Page<Message>>, response: Response<Page<Message>>) {
                    if (response.isSuccessful) {
                        val page = response.body()
                        if (page != null) {
                            messages.clear()
                            messages.addAll(page.results)
                            adapter.notifyDataSetChanged()
                            binding.rvMessages.scrollToPosition(messages.size - 1)
                        }
                    }
                }

                override fun onFailure(call: Call<Page<Message>>, t: Throwable) {
                    Toast.makeText(this@ChatActivity, "Ошибка загрузки", Toast.LENGTH_SHORT).show()
                }
            })
    }

    override fun onDestroy() {
        webSocketManager.disconnect()
        super.onDestroy()
    }
}
