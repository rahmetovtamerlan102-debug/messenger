package com.example.messenger

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.example.messenger.databinding.ActivityProfileBinding
import com.example.messenger.network.ApiClient
import com.example.messenger.utils.TokenManager
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class ProfileActivity : AppCompatActivity() {
    private lateinit var binding: ActivityProfileBinding
    private lateinit var tokenManager: TokenManager

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityProfileBinding.inflate(layoutInflater)
        setContentView(binding.root)

        tokenManager = TokenManager(this)
        val token = tokenManager.getAccessToken()
        if (token == null) {
            finish()
            return
        }

        loadProfile()

        binding.btnLogout.setOnClickListener {
            tokenManager.clear()
            finish()
        }
    }

    private fun loadProfile() {
        val token = tokenManager.getAccessToken() ?: return
        ApiClient.getApiService(this).getProfile("Bearer $token")
            .enqueue(object : Callback<UserProfile> {
                override fun onResponse(call: Call<UserProfile>, response: Response<UserProfile>) {
                    if (response.isSuccessful) {
                        val profile = response.body()
                        if (profile != null) {
                            binding.tvUsername.text = profile.user.username
                            binding.tvBio.text = profile.bio ?: "Био отсутствует"
                        }
                    }
                }

                override fun onFailure(call: Call<UserProfile>, t: Throwable) {
                    Toast.makeText(this@ProfileActivity, "Ошибка загрузки", Toast.LENGTH_SHORT).show()
                }
            })
    }
}
